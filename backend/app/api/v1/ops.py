"""Operations area: case queue + detail (AI-6 + AI-7 + Dispute Clock), human actions with audit, QR watchlist (AI-5)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app import db
from app.api.v1.deps import engines, envelope
from app.core.security import require

router = APIRouter(tags=["operations"])


class ActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["request_evidence", "approve_hold", "escalate", "dismiss", "close", "note"]
    reason: str = Field(min_length=10, max_length=500)


@router.get("/cases")
def cases(request: Request, limit: int = 50, user: dict = Depends(require("ops"))) -> dict:
    s = engines()
    limit = max(1, min(limit, 300))
    return envelope(request, {"cases": s.cases.queue(limit, db.statuses()), "total": len(s.cases.cases),
                              "now": s.cases.now_t}, f"ai6-{s.cases.source}")


@router.get("/cases/{case_key}")
def case_detail(case_key: str, request: Request, user: dict = Depends(require("ops"))) -> dict:
    s = engines()
    if case_key not in s.cases.by_key:
        raise HTTPException(404, "Unknown case")
    d = s.cases.detail(case_key)
    brief = s.briefs.for_case(s.cases.by_key[case_key])
    d["brief"] = {k: v for k, v in brief.items() if k != "evidence_object"}
    d["status"] = db.statuses().get(case_key, "open")
    d["actions"] = db.actions(case_key)
    return envelope(request, d, f"ai6-{s.cases.source}")


@router.post("/cases/{case_key}/actions")
def case_action(case_key: str, body: ActionIn, request: Request, user: dict = Depends(require("ops"))) -> dict:
    s = engines()
    if case_key not in s.cases.by_key:
        raise HTTPException(404, "Unknown case")
    trace = getattr(request.state, "trace_id", "")
    out = db.record_action(case_key, body.action, body.reason, user["role"], user["sub"], trace)
    db.audit(user["sub"], f"/cases/{case_key}/actions", trace, f"{body.action}: {body.reason}")
    return envelope(request, {**out, "message": "Recorded. A person made this decision; the AI only recommended."})


@router.get("/qr/merchants")
def qr_watchlist(request: Request, state: str | None = None, limit: int = 50, user: dict = Depends(require("ops"))) -> dict:
    s = engines()
    return envelope(request, {"merchants": s.qr.watchlist(state, max(1, min(limit, 300))), "counts": s.qr.counts()}, s.qr.version)


@router.get("/qr/merchants/{merchant_id}")
def qr_merchant(merchant_id: str, request: Request, user: dict = Depends(require("ops"))) -> dict:
    s = engines()
    try:
        return envelope(request, s.qr.merchant(merchant_id), s.qr.version)
    except KeyError as e:
        raise HTTPException(404, "Merchant not in the scored set") from e
