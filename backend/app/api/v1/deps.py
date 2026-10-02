"""Shared helpers for routes: readiness guard and the common response envelope."""
from __future__ import annotations

import time

from fastapi import HTTPException, Request

from app.core.config import settings
from app.state import state


def engines():
    if state.error:
        raise HTTPException(503, {"status": "failed", "detail": "The AI engines failed to start", "error": state.error[-300:]})
    if not state.ready:
        raise HTTPException(503, {"status": "warming_up", "detail": "The AI engines are starting (about a minute)",
                                  "progress": state.progress[-3:]})
    return state


def envelope(request: Request, body: dict, model_version: str = "", degraded: bool = False, reason: str | None = None) -> dict:
    return {"trace_id": getattr(request.state, "trace_id", ""), "model_version": model_version,
            "data_version": getattr(state, "data_version", "unknown"), "api_version": settings.app_version,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "degraded": degraded,
            "degraded_reason": reason, "synthetic_data": True, **body}
