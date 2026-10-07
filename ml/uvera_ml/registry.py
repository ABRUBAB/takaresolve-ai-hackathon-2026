"""Model registry and artifact integrity.

Every file the API serves is pinned by SHA-256 in `artifacts/registry.json` (and mirrored in `artifacts/manifest.json`).
Each model (ai1..ai7, plus the `web` data asset) has a list of versions with a status (approved | candidate | retired),
who approved it and when, and a pointer to its evaluation report. Only an *approved* active version whose files all match
their hashes may be served. Older versions are kept under `artifacts/_versions/<model>/<version>/`, so a rollback is one
command (see scripts/model_registry.py and docs/model_registry.md).

Standard library only: shared by the API (startup check) and the command-line tool.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

REGISTRY = "registry.json"
MANIFEST = "manifest.json"
VERSIONS_DIR = "_versions"
STATUSES = ("approved", "candidate", "retired")
SKIP = {REGISTRY, MANIFEST, "README.md"}


class RegistryError(RuntimeError):
    pass


# ------------------------------------------------------------------ helpers
def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json_atomic(path: Path, data: dict) -> None:
    """Write to a temp file in the same folder, then rename: a crash never leaves a half-written registry."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _manifest_rel(path: str) -> str:
    """manifest.json lists 'artifacts/ai1/model.txt'; the registry stores paths relative to the model folder: 'ai1/model.txt'."""
    return path[len("artifacts/"):] if path.startswith("artifacts/") else path


def load_registry(model_dir: str | Path) -> dict:
    p = Path(model_dir) / REGISTRY
    if not p.exists():
        raise RegistryError(f"{REGISTRY} not found in {model_dir}")
    try:
        reg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RegistryError(f"{REGISTRY} is not valid JSON: {e}") from e
    if not isinstance(reg.get("models"), dict):
        raise RegistryError(f"{REGISTRY} has no 'models' table")
    return reg


def save_registry(model_dir: str | Path, reg: dict) -> None:
    _write_json_atomic(Path(model_dir) / REGISTRY, reg)


def load_manifest(model_dir: str | Path) -> dict:
    p = Path(model_dir) / MANIFEST
    if not p.exists():
        raise RegistryError(f"{MANIFEST} not found in {model_dir}")
    return json.loads(p.read_text(encoding="utf-8"))


def get_version(reg: dict, model: str, version: str) -> dict:
    if model not in reg["models"]:
        raise RegistryError(f"unknown model '{model}' (known: {', '.join(reg['models'])})")
    for v in reg["models"][model]["versions"]:
        if v["version"] == version:
            return v
    raise RegistryError(f"{model} has no version '{version}'")


def archive_dir(model_dir: str | Path, model: str, version: str) -> Path:
    return Path(model_dir) / VERSIONS_DIR / model / version


def _archived_path(model_dir: Path, model: str, version: str, rel: str) -> Path:
    return archive_dir(model_dir, model, version) / rel.split("/", 1)[1]


def _files_match(base: Callable[[str], Path], files: list[dict]) -> list[str]:
    """Problems for a list of {path, sha256} files, where base(rel) gives the file location."""
    problems = []
    for f in files:
        p = base(f["path"])
        if not p.is_file():
            problems.append(f"{f['path']}: missing")
        elif sha256_file(p) != f["sha256"]:
            problems.append(f"{f['path']}: sha256 mismatch")
    return problems


# ------------------------------------------------------------------ the startup check
def verify(model_dir: str | Path) -> dict:
    """Check the ACTIVE version of every model: approved, every file present, SHA-256 as registered, and listed with the
    same hash in manifest.json (a manifest written after the registry means the artifacts were rebuilt: stale).

    Returns {"ok", "checked_at", "model_dir", "models": {model: {version, status, verified, files, problems}},
    "bad_files": [{"model", "path", "problem"}], "problems": [global problems]}.
    """
    model_dir = Path(model_dir)
    out = {"ok": False, "checked_at": now_iso(), "model_dir": str(model_dir), "models": {}, "bad_files": [], "problems": []}
    try:
        reg = load_registry(model_dir)
    except RegistryError as e:
        out["problems"].append(str(e))
        return out
    try:
        manifest = {_manifest_rel(a["path"]): a for a in load_manifest(model_dir).get("artifacts", [])}
    except (RegistryError, json.JSONDecodeError) as e:
        out["problems"].append(f"manifest: {e}")
        manifest = None
    registered = set()
    for model, entry in reg["models"].items():
        active = entry.get("active")
        info = {"version": active, "status": None, "verified": False, "files": 0, "problems": []}
        out["models"][model] = info
        try:
            v = get_version(reg, model, active)
        except RegistryError as e:
            info["problems"].append(f"no usable active version: {e}")
            continue
        info["status"] = v.get("status")
        info["files"] = len(v.get("files", []))
        if v.get("status") != "approved":
            info["problems"].append(f"active version {active} is not approved (status: {v.get('status')})")
        for f in v.get("files", []):
            rel = f["path"]
            registered.add(rel)
            p = model_dir / rel
            problem = None
            if not p.is_file():
                problem = "missing"
            elif sha256_file(p) != f["sha256"]:
                problem = "sha256 mismatch: file changed, stale or tampered"
            elif manifest is not None and rel not in manifest:
                problem = "not listed in manifest.json"
            elif manifest is not None and manifest[rel]["sha256"] != f["sha256"]:
                problem = "manifest.json lists a different sha256 (artifacts rebuilt without a registry update)"
            if problem:
                info["problems"].append(f"{rel}: {problem}")
                out["bad_files"].append({"model": model, "path": rel, "problem": problem})
        info["verified"] = not info["problems"]
    if manifest is not None:
        for rel in sorted(set(manifest) - registered):
            out["problems"].append(f"{rel}: listed in manifest.json but not registered to any model version")
            out["bad_files"].append({"model": rel.split("/")[0], "path": rel, "problem": "unregistered artifact"})
    out["ok"] = not out["problems"] and all(m["verified"] for m in out["models"].values()) and bool(out["models"])
    return out


def summary(report: dict) -> dict:
    """The small public block for /v1/health/ready and /v1/meta: version, status and verified flag per model."""
    return {m: {"version": i["version"], "status": i["status"], "verified": i["verified"]} for m, i in report["models"].items()}


# ------------------------------------------------------------------ registry changes (used by scripts/model_registry.py)
def _history(reg: dict, action: str, model: str, version: str, by: str, notes: str = "") -> None:
    reg.setdefault("history", []).append({"at": now_iso(), "action": action, "model": model, "version": version, "by": by,
                                          "notes": notes})


def init_from_manifest(model_dir: str | Path, approved_by: str, approved_at: str, version: str = "v1",
                       metrics_dir: str = "reports", notes: str = "") -> dict:
    """Build registry.json from the current manifest: every model's current files become its first approved version."""
    model_dir = Path(model_dir)
    manifest = load_manifest(model_dir)
    repo = model_dir.parent
    models: dict[str, dict] = {}
    for a in manifest["artifacts"]:
        rel = _manifest_rel(a["path"])
        model = rel.split("/")[0]
        m = models.setdefault(model, {"active": version, "versions": [{
            "version": version, "status": "approved", "approved_by": approved_by, "approved_at": approved_at,
            "notebook": a.get("notebook"), "code_commit": a.get("code_commit"), "data_version": manifest.get("data_version"),
            "files": [], "notes": notes}]})
        m["versions"][0]["files"].append({"path": rel, "bytes": a["bytes"], "sha256": a["sha256"]})
    for model, m in models.items():
        v = m["versions"][0]
        metrics = repo / metrics_dir / f"metrics_{model}.json"
        card = repo / metrics_dir / "model_cards" / f"{model.upper().replace('AI', 'AI-')}.md"
        v["metrics"] = {"report": f"{metrics_dir}/metrics_{model}.json", "sha256": sha256_file(metrics)} if metrics.exists() else None
        v["model_card"] = f"{metrics_dir}/model_cards/{card.name}" if card.exists() else None
    reg = {"schema_version": 1,
           "about": "Model registry: the served version of every model, its file hashes, approval and history. "
                    "Edit only with scripts/model_registry.py (see docs/model_registry.md).",
           "models": dict(sorted(models.items())), "history": []}
    _history(reg, "init", "*", version, approved_by, notes)
    return reg


def register(model_dir: str | Path, model: str, src: str | Path, version: str, by: str, notes: str = "",
             data_version: str | None = None, metrics: str | None = None) -> dict:
    """Add a CANDIDATE version from a folder of files. The files are copied to artifacts/_versions/<model>/<version>/."""
    model_dir, src = Path(model_dir), Path(src)
    reg = load_registry(model_dir)
    if model not in reg["models"]:
        raise RegistryError(f"unknown model '{model}'")
    if any(v["version"] == version for v in reg["models"][model]["versions"]):
        raise RegistryError(f"{model} already has a version '{version}'")
    files = sorted(p for p in src.rglob("*") if p.is_file() and p.name not in SKIP)
    if not files:
        raise RegistryError(f"no files in {src}")
    dest = archive_dir(model_dir, model, version)
    dest.mkdir(parents=True, exist_ok=False)
    rows = []
    for p in files:
        rel_in_model = p.relative_to(src).as_posix()
        (dest / rel_in_model).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest / rel_in_model)
        rows.append({"path": f"{model}/{rel_in_model}", "bytes": p.stat().st_size, "sha256": sha256_file(dest / rel_in_model)})
    current = get_version(reg, model, reg["models"][model]["active"])
    entry = {"version": version, "status": "candidate", "approved_by": None, "approved_at": None,
             "registered_by": by, "registered_at": now_iso(), "notebook": current.get("notebook"), "code_commit": None,
             "data_version": data_version or current.get("data_version"),
             "metrics": {"report": metrics, "sha256": sha256_file(model_dir.parent / metrics)}
             if metrics and (model_dir.parent / metrics).exists() else None,
             "files": rows, "notes": notes}
    reg["models"][model]["versions"].append(entry)
    _history(reg, "register", model, version, by, notes)
    save_registry(model_dir, reg)
    return entry


def _version_files_ok(model_dir: Path, reg: dict, model: str, v: dict) -> list[str]:
    """A version's files are checked where they live: the archive, or the live folder if it is the active version."""
    arch = archive_dir(model_dir, model, v["version"])
    if arch.exists():
        return _files_match(lambda rel: _archived_path(model_dir, model, v["version"], rel), v["files"])
    if reg["models"][model]["active"] == v["version"]:
        return _files_match(lambda rel: model_dir / rel, v["files"])
    return [f"no stored files for {model} {v['version']} (expected {arch})"]


def approve(model_dir: str | Path, model: str, version: str, by: str, notes: str = "") -> dict:
    """Mark a version approved after re-checking that its stored files still match their hashes."""
    model_dir = Path(model_dir)
    if not by or not by.strip():
        raise RegistryError("approval needs a name (--by)")
    reg = load_registry(model_dir)
    v = get_version(reg, model, version)
    problems = _version_files_ok(model_dir, reg, model, v)
    if problems:
        raise RegistryError("cannot approve, files do not match their hashes: " + "; ".join(problems))
    v.update(status="approved", approved_by=by.strip(), approved_at=now_iso())
    if notes:
        v["notes"] = (v.get("notes") + " | " if v.get("notes") else "") + notes
    _history(reg, "approve", model, version, by, notes)
    save_registry(model_dir, reg)
    return v


def _update_manifest(model_dir: Path, model: str, v: dict) -> None:
    manifest = load_manifest(model_dir)
    keep = [a for a in manifest["artifacts"] if _manifest_rel(a["path"]).split("/")[0] != model]
    new = [{"path": f"artifacts/{f['path']}", "bytes": f["bytes"], "sha256": f["sha256"], "notebook": v.get("notebook"),
            "code_commit": v.get("code_commit")} for f in v["files"]]
    manifest["artifacts"] = sorted(keep + new, key=lambda a: a["path"])
    _write_json_atomic(model_dir / MANIFEST, manifest)


def activate(model_dir: str | Path, model: str, version: str, by: str, notes: str = "", _action: str = "activate") -> dict:
    """Serve an APPROVED version: archive the current files, copy the version's files into artifacts/<model>/,
    update manifest.json, then re-verify. Candidates and retired versions are refused."""
    model_dir = Path(model_dir)
    reg = load_registry(model_dir)
    entry = reg["models"].get(model)
    if entry is None:
        raise RegistryError(f"unknown model '{model}'")
    target = get_version(reg, model, version)
    if target["status"] != "approved":
        raise RegistryError(f"{model} {version} is {target['status']}, only approved versions can be served")
    current = get_version(reg, model, entry["active"])
    if current["version"] == version:
        raise RegistryError(f"{model} {version} is already active")
    problems = _files_match(lambda rel: _archived_path(model_dir, model, version, rel), target["files"])
    if problems:
        raise RegistryError(f"stored files of {model} {version} do not match: " + "; ".join(problems))
    # 1. archive the current version (only if the live files really are that version)
    arch = archive_dir(model_dir, model, current["version"])
    live_ok = not _files_match(lambda rel: model_dir / rel, current["files"])
    if live_ok and not arch.exists():
        tmp = arch.with_name(arch.name + ".partial")
        shutil.rmtree(tmp, ignore_errors=True)
        for f in current["files"]:
            dst = tmp / f["path"].split("/", 1)[1]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(model_dir / f["path"], dst)
        tmp.rename(arch)
    # 2. replace the live files
    for f in current["files"]:
        p = model_dir / f["path"]
        if p.exists():
            p.unlink()
    for f in target["files"]:
        dst = model_dir / f["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_archived_path(model_dir, model, version, f["path"]), dst)
    # 3. record it
    _update_manifest(model_dir, model, target)
    entry["active"] = version
    _history(reg, _action, model, version, by, notes or f"replaces {current['version']}")
    save_registry(model_dir, reg)
    report = verify(model_dir)
    if not report["models"][model]["verified"]:
        raise RegistryError(f"{model} {version} activated but does not verify: {report['models'][model]['problems']}")
    return {"model": model, "active": version, "previous": current["version"], "verified": True}


def previous_approved(reg: dict, model: str) -> dict | None:
    """The approved version listed just before the active one (else the newest other approved version)."""
    versions = reg["models"][model]["versions"]
    idx = next(i for i, v in enumerate(versions) if v["version"] == reg["models"][model]["active"])
    before = [v for v in versions[:idx] if v["status"] == "approved"]
    after = [v for v in versions[idx + 1:] if v["status"] == "approved"]
    return (before or after or [None])[-1]


def rollback(model_dir: str | Path, model: str, by: str, reason: str = "") -> dict:
    """Serve the previous approved version again; the rolled-back version is marked retired."""
    model_dir = Path(model_dir)
    reg = load_registry(model_dir)
    if model not in reg["models"]:
        raise RegistryError(f"unknown model '{model}'")
    prev = previous_approved(reg, model)
    if prev is None:
        raise RegistryError(f"{model} has no other approved version to roll back to")
    bad = reg["models"][model]["active"]
    out = activate(model_dir, model, prev["version"], by, f"rollback from {bad}: {reason}".strip(": "), _action="rollback")
    reg = load_registry(model_dir)
    v = get_version(reg, model, bad)
    v["status"] = "retired"
    v["notes"] = (v.get("notes") + " | " if v.get("notes") else "") + f"retired by rollback on {now_iso()} by {by}: {reason}"
    save_registry(model_dir, reg)
    return {**out, "retired": bad}
