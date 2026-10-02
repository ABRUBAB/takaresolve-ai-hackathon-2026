"""Liveness and readiness checks."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.state import state

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    if state.ready:
        return JSONResponse({"status": "ready", "progress": state.progress[-1:]})
    status = "failed" if state.error else "warming_up"
    return JSONResponse({"status": status, "progress": state.progress[-3:]}, status_code=503)
