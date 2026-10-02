from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_live() -> None:
    response = client.get("/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_missing_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "model_dir", str(tmp_path))
    response = client.get("/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["artifact_manifest"] is False


def test_ready_when_manifest_present(tmp_path, monkeypatch) -> None:
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "model_dir", str(tmp_path))
    assert client.get("/v1/health/ready").status_code == 200
