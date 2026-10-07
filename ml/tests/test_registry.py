"""Model registry: approval gate, versions, activation and rollback on a temp copy of artifacts/."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from uvera_ml import registry as R

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def arts(tmp_path):
    dst = tmp_path / "artifacts"
    shutil.copytree(ROOT / "artifacts", dst, ignore=shutil.ignore_patterns("_versions"))
    return dst


def new_version_folder(arts: Path, tmp_path: Path) -> Path:
    """A 'retrained' AI-1: same files, one threshold changed."""
    src = tmp_path / "ai1_v2"
    shutil.copytree(arts / "ai1", src)
    p = src / "thresholds.json"
    p.write_text(p.read_text(encoding="utf-8").replace("0.", "0.0", 1), encoding="utf-8")
    return src


def test_verify_ok_and_detects_tampering(arts):
    assert R.verify(arts)["ok"]
    p = arts / "ai4" / "residuals.json"
    p.write_bytes(p.read_bytes() + b" ")
    rep = R.verify(arts)
    assert not rep["ok"]
    assert rep["bad_files"] == [{"model": "ai4", "path": "ai4/residuals.json",
                                 "problem": "sha256 mismatch: file changed, stale or tampered"}]


def test_unregistered_artifact_in_manifest_is_reported(arts):
    import json

    m = json.loads((arts / "manifest.json").read_text(encoding="utf-8"))
    m["artifacts"].append({"path": "artifacts/ai1/extra.bin", "bytes": 1, "sha256": "0" * 64})
    (arts / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    rep = R.verify(arts)
    assert not rep["ok"] and rep["bad_files"][-1]["problem"] == "unregistered artifact"


def test_candidate_cannot_be_activated(arts, tmp_path):
    R.register(arts, "ai1", new_version_folder(arts, tmp_path), "v2", by="tester")
    with pytest.raises(R.RegistryError, match="only approved versions"):
        R.activate(arts, "ai1", "v2", by="tester")
    assert R.verify(arts)["ok"]  # nothing changed in the served files


def test_approval_refuses_tampered_archive(arts, tmp_path):
    R.register(arts, "ai1", new_version_folder(arts, tmp_path), "v2", by="tester")
    stored = R.archive_dir(arts, "ai1", "v2") / "thresholds.json"
    stored.write_text("{}", encoding="utf-8")
    with pytest.raises(R.RegistryError, match="do not match"):
        R.approve(arts, "ai1", "v2", by="reviewer")


def test_register_approve_activate_then_rollback_restores_v1(arts, tmp_path):
    v1_hashes = {f.relative_to(arts).as_posix(): R.sha256_file(f) for f in (arts / "ai1").iterdir()}
    R.register(arts, "ai1", new_version_folder(arts, tmp_path), "v2", by="tester", notes="threshold experiment")
    R.approve(arts, "ai1", "v2", by="reviewer")
    out = R.activate(arts, "ai1", "v2", by="reviewer")
    assert out == {"model": "ai1", "active": "v2", "previous": "v1", "verified": True}
    assert R.sha256_file(arts / "ai1" / "thresholds.json") != v1_hashes["ai1/thresholds.json"]
    assert R.verify(arts)["ok"]  # manifest.json was updated together with the registry
    assert (R.archive_dir(arts, "ai1", "v1") / "model.txt").exists()  # v1 kept for rollback

    out = R.rollback(arts, "ai1", by="on-call", reason="false-positive spike")
    assert out["active"] == "v1" and out["retired"] == "v2"
    now = {f.relative_to(arts).as_posix(): R.sha256_file(f) for f in (arts / "ai1").iterdir()}
    assert now == v1_hashes  # byte-identical to the original approved version
    rep = R.verify(arts)
    assert rep["ok"] and rep["models"]["ai1"] == {"version": "v1", "status": "approved", "verified": True, "files": 7,
                                                  "problems": []}
    reg = R.load_registry(arts)
    assert R.get_version(reg, "ai1", "v2")["status"] == "retired"
    assert [h["action"] for h in reg["history"]][-4:] == ["register", "approve", "activate", "rollback"]


def test_rollback_without_previous_version_is_refused(arts):
    with pytest.raises(R.RegistryError, match="no other approved version"):
        R.rollback(arts, "ai2", by="on-call")


def test_cli_verify_exit_codes(arts):
    cmd = [sys.executable, str(ROOT / "scripts" / "model_registry.py"), "--model-dir", str(arts), "verify"]
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 0
    p = arts / "ai6" / "cases.json"
    p.write_bytes(p.read_bytes()[:-1])
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1 and "ai6/cases.json" in res.stdout
