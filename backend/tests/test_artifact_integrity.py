"""Stale / tampered model artifacts: the API must refuse to serve and say which file is wrong; after a restore it serves.

The artifacts are copied to a temp folder and the app is pointed at it (MODEL_DIR). The startup path is the real one
(state.load -> SHA-256 + approval check); only the heavy engine loading after a successful check is replaced by a stub,
so these tests run in seconds and in CI.
"""
import shutil
from pathlib import Path

import pytest
from app.core.config import settings
from app.core.security import issue
from app.main import app
from app.state import state
from fastapi.testclient import TestClient
from uvera_ml import registry as R

REPO_ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
client = TestClient(app)


@pytest.fixture
def model_dir(tmp_path, monkeypatch):
    dst = tmp_path / "artifacts"
    shutil.copytree(REPO_ARTIFACTS, dst, ignore=shutil.ignore_patterns("_versions"))
    monkeypatch.setattr(settings, "model_dir", str(dst))
    saved = (state.ready, state.error, state.integrity)
    monkeypatch.setattr(state, "_load_engines", lambda: setattr(state, "ready", True))  # engines are not under test
    yield dst
    state.ready, state.error, state.integrity = saved


def flip_byte(p: Path, offset: int = 100) -> bytes:
    data = bytearray(p.read_bytes())
    original = bytes(data)
    data[offset] ^= 0x01
    p.write_bytes(bytes(data))
    return original


def test_repository_artifacts_verify():
    report = R.verify(REPO_ARTIFACTS)
    assert report["ok"], report["bad_files"] + report["problems"]
    assert {"ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7"} <= set(report["models"])
    assert all(m["status"] == "approved" and m["verified"] for m in report["models"].values())


def test_clean_copy_is_ready_with_models_block(model_dir):
    state.load()
    r = client.get("/v1/health/ready")
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["status"] == "ready" and body["artifacts_verified"] is True
    assert body["models"]["ai1"] == {"version": "v1", "status": "approved", "verified": True}


def test_one_flipped_byte_blocks_serving_and_names_the_file(model_dir):
    target = model_dir / "ai1" / "model.txt"
    original = flip_byte(target)
    state.load()
    r = client.get("/v1/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "failed"
    assert [b["path"] for b in body["bad_files"]] == ["ai1/model.txt"]
    assert "sha256 mismatch" in body["bad_files"][0]["problem"]
    assert body["models"]["ai1"]["verified"] is False and body["models"]["ai2"]["verified"] is True
    # model endpoints refuse to serve (503), they do not run on the tampered file
    tok = {"Authorization": f"Bearer {issue('ops', 'OPS-TEST')}"}
    assert client.get("/v1/cases", headers=tok).status_code == 503
    assert "ai1/model.txt" in client.get("/v1/meta").json()["detail"]["error"]
    # restore the byte: the next start serves again
    target.write_bytes(original)
    state.load()
    assert client.get("/v1/health/ready").status_code == 200


def test_missing_file_blocks_serving(model_dir):
    (model_dir / "ai5" / "calibrator.json").unlink()
    state.load()
    r = client.get("/v1/health/ready")
    assert r.status_code == 503
    assert {"model": "ai5", "path": "ai5/calibrator.json", "problem": "missing"} in r.json()["bad_files"]


def test_unapproved_active_version_blocks_serving(model_dir):
    reg = R.load_registry(model_dir)
    reg["models"]["ai3"]["versions"][0]["status"] = "candidate"
    R.save_registry(model_dir, reg)
    state.load()
    r = client.get("/v1/health/ready")
    assert r.status_code == 503
    assert r.json()["models"]["ai3"] == {"version": "v1", "status": "candidate", "verified": False}


def test_stale_manifest_is_detected(model_dir):
    """Artifacts rebuilt (manifest rewritten) without a registry update = stale: refused."""
    import json

    m = json.loads((model_dir / "manifest.json").read_text(encoding="utf-8"))
    m["artifacts"][0]["sha256"] = "0" * 64
    (model_dir / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    state.load()
    r = client.get("/v1/health/ready")
    assert r.status_code == 503
    assert "manifest.json lists a different sha256" in r.json()["bad_files"][0]["problem"]


def test_missing_registry_fails_closed(model_dir):
    (model_dir / "registry.json").unlink()
    state.load()
    r = client.get("/v1/health/ready")
    assert r.status_code == 503
    assert any("registry.json not found" in p for p in r.json()["problems"])


def test_warn_mode_serves_but_reports_unverified(model_dir, monkeypatch):
    monkeypatch.setattr(settings, "artifact_verify", "warn")
    flip_byte(model_dir / "ai2" / "model_info.json")
    state.load()
    r = client.get("/v1/health/ready")
    assert r.status_code == 200
    assert r.json()["artifacts_verified"] is False and r.json()["models"]["ai2"]["verified"] is False
