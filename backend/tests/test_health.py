import os

os.environ["WARM_ON_START"] = "false"  # tests never load the full world

from app.core.security import issue  # noqa: E402
from app.main import app  # noqa: E402
from app.state import state  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)


def test_live() -> None:
    response = client.get("/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_warming_up_before_engines_load() -> None:
    state.ready = False
    response = client.get("/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "warming_up"


def test_every_response_carries_a_trace_id() -> None:
    assert client.get("/v1/health/live").headers.get("x-trace-id")


def test_ops_endpoints_need_the_ops_role() -> None:
    assert client.get("/v1/cases").status_code == 401
    customer = {"Authorization": f"Bearer {issue('customer', 'C000001')}"}
    assert client.get("/v1/cases", headers=customer).status_code == 403


def test_customers_cannot_read_other_customers() -> None:
    customer = {"Authorization": f"Bearer {issue('customer', 'C000001')}"}
    assert client.get("/v1/customers/C000002/profile", headers=customer).status_code == 403


def test_input_validation_rejects_bad_requests() -> None:
    customer = {"Authorization": f"Bearer {issue('customer', 'C000001')}"}
    bad = {"sender_id": "C000001", "recipient_wallet": "C000002", "amount": -5}
    assert client.post("/v1/pause-check", json=bad, headers=customer).status_code == 422
    extra = {"sender_id": "C000001", "recipient_wallet": "C000002", "amount": 100, "hack": True}
    assert client.post("/v1/pause-check", json=extra, headers=customer).status_code == 422


def test_engines_not_ready_returns_503_not_a_crash() -> None:
    state.ready = False
    customer = {"Authorization": f"Bearer {issue('customer', 'C000001')}"}
    ok = {"sender_id": "C000001", "recipient_wallet": "C000002", "amount": 100}
    assert client.post("/v1/pause-check", json=ok, headers=customer).status_code == 503
