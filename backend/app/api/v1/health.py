"""Liveness and readiness checks."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.state import state

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


def _models() -> dict:
    """Per model: served version, approval status and whether its files matched their SHA-256 at startup."""
    from uvera_ml.registry import summary

    return summary(state.integrity) if state.integrity else {}


@router.get("/ready")
def ready() -> JSONResponse:
    integrity_ok = state.integrity is None or state.integrity["ok"]
    if state.ready:
        return JSONResponse({"status": "ready", "progress": state.progress[-1:], "models": _models(),
                             "artifacts_verified": integrity_ok})
    status = "failed" if state.error else "warming_up"
    body = {"status": status, "progress": state.progress[-3:], "models": _models()}
    if not integrity_ok:
        body.update(reason="Model artifact integrity check failed: these files are missing, changed (stale or tampered) "
                           "or their version is not approved, so the models are not served.",
                    bad_files=state.integrity["bad_files"], problems=state.integrity["problems"])
    return JSONResponse(body, status_code=503)
