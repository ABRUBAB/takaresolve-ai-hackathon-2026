import os

os.environ["WARM_ON_START"] = "false"  # tests never load the full world

import sqlite3  # noqa: E402
import uuid  # noqa: E402

import pytest  # noqa: E402
from app import db  # noqa: E402
from app.api.v1 import study  # noqa: E402
from app.core.security import issue  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)
PIN = {"X-Study-Pin": "uvera2026"}


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test writes to its own throwaway database, never the real one."""
    c = sqlite3.connect(tmp_path / "study.db", check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    monkeypatch.setattr(db, "_conn", c)
    monkeypatch.setattr(study, "_ready", False)
    monkeypatch.setattr(study.settings, "study_results_pin", "uvera2026")
    study._submits.clear()
    study._wrong_pins.clear()
    yield
    c.close()


def response(arm="A", rings=3, wallet="W-77", q1="paused_scam", q2="wait", **extra) -> dict:
    return {
        "study_version": "s1-test",
        "client_id": uuid.uuid4().hex,
        "consent": True,
        "facilitator": "F1",
        "ui_lang": "bn",
        "assignment": f"{arm}-bn",
        "total_ms": 240000,
        "profile": {"age_band": "18-24", "mm_use": "daily", "phone_lang": "bn", "scam_contact": "yes", "scam_loss": "no"},
        "task1": {"lang": "bn", "q1_meaning": q1, "q2_action": q2, "q3_reason": "senders", "q4_clarity": 5, "q5_trust": 4,
                  "q6_annoyance": 2, "view_ms": 9000, "total_ms": 60000},
        "task2": {"lang": "bn", "q_next": "person_checks", "q_ok_unsure": 4, "view_ms": 5000, "total_ms": 20000},
        "task3": {"arm": arm, "rings": rings, "first_wallet": wallet, "time_ms": 45000, "confidence": 4},
        **extra,
    }


def test_submit_without_login_and_read_results_with_pin() -> None:
    assert client.post("/v1/study/responses", json=response("A", rings=4, wallet="W-31", q2="send_anyway")).status_code == 201
    out = client.post("/v1/study/responses", json=response("B"))
    assert out.status_code == 201 and out.json()["participant_id"].startswith("P-")
    res = client.get("/v1/study/results", headers=PIN)
    assert res.status_code == 200
    s = res.json()["summary"]
    assert s["n"] == 2
    assert s["task1"]["comprehension"]["rate"] == 1.0
    assert s["task1"]["stated_stop"]["k"] == 1
    assert s["task3"]["A"]["both_correct"]["k"] == 0 and s["task3"]["B"]["both_correct"]["k"] == 1
    assert all("client_id" not in r for r in res.json()["rows"])


def test_results_need_pin_or_ops_role() -> None:
    assert client.get("/v1/study/results").status_code == 401
    assert client.get("/v1/study/results", headers={"X-Study-Pin": "wrong"}).status_code == 401
    customer = {"Authorization": f"Bearer {issue('customer', 'C000001')}"}
    assert client.get("/v1/study/results", headers=customer).status_code == 403
    ops = {"Authorization": f"Bearer {issue('ops', 'OPS01')}"}
    assert client.get("/v1/study/results", headers=ops).status_code == 200
    assert client.get("/v1/study/export.csv").status_code == 401


def test_wrong_pins_are_rate_limited() -> None:
    for _ in range(study.WRONG_PINS_PER_10_MIN):
        client.get("/v1/study/results", headers={"X-Study-Pin": "guess"})
    assert client.get("/v1/study/results", headers=PIN).status_code == 429


def test_personal_fields_are_rejected() -> None:
    assert client.post("/v1/study/responses", json=response(name="Rahim")).status_code == 422
    assert client.post("/v1/study/responses", json=response(phone="01711000000")).status_code == 422
    bad_profile = response()
    bad_profile["profile"]["name"] = "Rahim"
    assert client.post("/v1/study/responses", json=bad_profile).status_code == 422


def test_phone_numbers_and_emails_are_removed_from_comments() -> None:
    body = response(comment="Call me on 01711-000000 or +880 1811 222333, mail me@example.com. Clear screen!")
    assert client.post("/v1/study/responses", json=body).status_code == 201
    comment = client.get("/v1/study/results", headers=PIN).json()["rows"][0]["comment"]
    assert "01711" not in comment and "1811" not in comment and "example.com" not in comment
    assert "Clear screen!" in comment


def test_validation_size_and_consent() -> None:
    assert client.post("/v1/study/responses", json=response(consent=False)).status_code == 422
    bad = response()
    bad["task1"]["q4_clarity"] = 9
    assert client.post("/v1/study/responses", json=bad).status_code == 422
    assert client.post("/v1/study/responses", json=response(comment="x" * 601)).status_code == 422
    assert client.post("/v1/study/responses", content=b"{" + b" " * 21000 + b"}",
                       headers={"Content-Type": "application/json"}).status_code == 413


def test_a_retried_upload_is_stored_once() -> None:
    body = response()
    first = client.post("/v1/study/responses", json=body).json()
    again = client.post("/v1/study/responses", json=body).json()
    assert again["duplicate"] is True and again["participant_id"] == first["participant_id"]
    assert client.get("/v1/study/results", headers=PIN).json()["summary"]["n"] == 1


def test_csv_export() -> None:
    client.post("/v1/study/responses", json=response(comment="=HYPERLINK(1)"))
    res = client.get("/v1/study/export.csv", headers=PIN)
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/csv")
    header, row = res.text.strip().splitlines()[:2]
    assert "task3.arm" in header and "participant_id" in header
    assert "'=HYPERLINK" in row
