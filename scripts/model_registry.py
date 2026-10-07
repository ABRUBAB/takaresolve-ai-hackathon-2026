"""Model registry command line: which version of each model is served, approvals, rollback, integrity check.

    python scripts/model_registry.py status                          # active version, status, verified per model
    python scripts/model_registry.py verify                          # SHA-256 + approval check (exit 1 if anything fails)
    python scripts/model_registry.py register ai1 --from NEW_DIR --version v2 --by "Name" [--notes ...]
    python scripts/model_registry.py approve ai1 v2 --by "Name" [--notes ...]
    python scripts/model_registry.py activate ai1 v2 --by "Name"    # serve an approved version
    python scripts/model_registry.py rollback ai1 --by "Name" --reason "..."
    python scripts/model_registry.py history [ai1]
    python scripts/model_registry.py init --by "team (phase-1 release)" --at 2026-10-03T22:32:31Z   # once, from manifest.json

--model-dir (or the MODEL_DIR environment variable) selects the artifacts folder; default: artifacts/ in this repo.
The API refuses to serve a model whose files do not verify or whose active version is not approved (restart it after a
change). See docs/model_registry.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml import registry as R  # noqa: E402


def _dir(args) -> Path:
    return Path(args.model_dir or os.environ.get("MODEL_DIR") or ROOT / "artifacts").resolve()


def cmd_status(args) -> int:
    d = _dir(args)
    reg = R.load_registry(d)
    rep = R.verify(d)
    print(f"model dir: {d}")
    print(f"{'model':<6} {'active':<8} {'status':<10} {'verified':<9} {'approved_by':<28} {'approved_at':<21} versions")
    for m, e in reg["models"].items():
        v = R.get_version(reg, m, e["active"])
        vers = ", ".join(f"{x['version']}({x['status']})" for x in e["versions"])
        print(f"{m:<6} {e['active']:<8} {v['status']:<10} {str(rep['models'][m]['verified']):<9} "
              f"{(v.get('approved_by') or '-'):<28} {(v.get('approved_at') or '-'):<21} {vers}")
    print("OVERALL:", "VERIFIED" if rep["ok"] else "NOT VERIFIED (the API will not serve these models)")
    return 0 if rep["ok"] else 1


def cmd_verify(args) -> int:
    rep = R.verify(_dir(args))
    if args.json:
        print(json.dumps(rep, indent=1))
    else:
        n = sum(i["files"] for i in rep["models"].values())
        print(f"checked {n} files in {len(rep['models'])} models at {rep['checked_at']}")
        for p in rep["problems"]:
            print("  PROBLEM", p)
        for b in rep["bad_files"]:
            print(f"  BAD {b['model']}: {b['path']}: {b['problem']}")
        for m, i in rep["models"].items():
            if i["problems"] and not any(b["model"] == m for b in rep["bad_files"]):
                print(f"  BAD {m}: {'; '.join(i['problems'])}")
        print("OK: every active model version is approved and every file matches its SHA-256" if rep["ok"] else "FAILED")
    return 0 if rep["ok"] else 1


def cmd_init(args) -> int:
    d = _dir(args)
    if (d / R.REGISTRY).exists() and not args.force:
        print(f"{d / R.REGISTRY} already exists (use --force to rebuild it from manifest.json)")
        return 1
    reg = R.init_from_manifest(d, args.by, args.at or R.now_iso(), args.version, notes=args.notes)
    R.save_registry(d, reg)
    print(f"wrote {d / R.REGISTRY}: {len(reg['models'])} models")
    return cmd_verify(argparse.Namespace(model_dir=str(d), json=False))


def cmd_register(args) -> int:
    v = R.register(_dir(args), args.model, args.src, args.version, args.by, args.notes, metrics=args.metrics)
    print(f"registered {args.model} {v['version']} as candidate ({len(v['files'])} files). Next: approve, then activate.")
    return 0


def cmd_approve(args) -> int:
    v = R.approve(_dir(args), args.model, args.version, args.by, args.notes)
    print(f"{args.model} {v['version']} approved by {v['approved_by']} at {v['approved_at']}")
    return 0


def cmd_activate(args) -> int:
    out = R.activate(_dir(args), args.model, args.version, args.by, args.notes)
    print(f"{out['model']}: now serving {out['active']} (was {out['previous']}), verified. Restart the API to load it.")
    return 0


def cmd_rollback(args) -> int:
    out = R.rollback(_dir(args), args.model, args.by, args.reason)
    print(f"{out['model']}: rolled back to {out['active']} (retired {out['retired']}), verified. Restart the API to load it.")
    return 0


def cmd_history(args) -> int:
    reg = R.load_registry(_dir(args))
    for h in reg.get("history", []):
        if not args.model or h["model"] in (args.model, "*"):
            print(f"{h['at']}  {h['action']:<9} {h['model']:<4} {h['version']:<8} by {h['by']}  {h.get('notes', '')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", help="artifacts folder (default: $MODEL_DIR or artifacts/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("verify")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("init")
    p.add_argument("--by", required=True)
    p.add_argument("--at", help="approval time (ISO 8601, UTC); default now")
    p.add_argument("--version", default="v1")
    p.add_argument("--notes", default="")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("register")
    p.add_argument("model")
    p.add_argument("--from", dest="src", required=True, help="folder with the new version's files")
    p.add_argument("--version", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--notes", default="")
    p.add_argument("--metrics", help="evaluation report for this version, relative to the repo (e.g. reports/metrics_ai1.json)")
    p.set_defaults(fn=cmd_register)
    p = sub.add_parser("approve")
    p.add_argument("model")
    p.add_argument("version")
    p.add_argument("--by", required=True)
    p.add_argument("--notes", default="")
    p.set_defaults(fn=cmd_approve)
    p = sub.add_parser("activate")
    p.add_argument("model")
    p.add_argument("version")
    p.add_argument("--by", required=True)
    p.add_argument("--notes", default="")
    p.set_defaults(fn=cmd_activate)
    p = sub.add_parser("rollback")
    p.add_argument("model")
    p.add_argument("--by", required=True)
    p.add_argument("--reason", default="")
    p.set_defaults(fn=cmd_rollback)
    p = sub.add_parser("history")
    p.add_argument("model", nargs="?")
    p.set_defaults(fn=cmd_history)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except R.RegistryError as e:
        print("ERROR:", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
