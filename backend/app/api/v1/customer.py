"""Customer area: profile, Pause Check (AI-1 + AI-2 + AI-7), Scam Text Check (AI-2), Cash-Flow Guardian (AI-3)."""
from __future__ import annotations

from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from uvera_ml.common import load_config
from uvera_ml.sim.world import START

from app.api.v1.deps import engines, envelope
from app.core.security import own, require
from app.core.telemetry import telemetry

router = APIRouter(tags=["customer"])
LIMITS = load_config("rules/limits")


class SimContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minutes_since_cash_in: float | None = Field(None, ge=0, le=1440)
    device_changed_recently: bool | None = None
    pin_reset_recently: bool | None = None


class PauseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender_id: str = Field(pattern=r"^C\d{6}$")
    recipient_wallet: str = Field(pattern=r"^C\d{6}$")
    amount: float = Field(gt=0, le=1_000_000)
    hour: float = Field(19.0, ge=0, lt=24)
    channel: Literal["app", "ussd"] = "app"
    note: str | None = Field(None, max_length=1000)
    simulated_context: SimContext | None = None

    @field_validator("amount", "hour", mode="before")
    @classmethod
    def _no_booleans(cls, v):
        if isinstance(v, bool):  # lax mode would read true as Tk 1
            raise ValueError("must be a number")
        return v


class TextIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=1000)


def _rule_hits(amount: float, first_time: bool) -> list[dict]:
    hits = []
    if amount > LIMITS["p2p_single_max_bdt"]:
        hits.append({"id": "RULE-LIMIT", "type": "business_rule", "text": f"Above the single-transfer limit (Tk {LIMITS['p2p_single_max_bdt']:,})"})
    if amount >= LIMITS["rule_baseline"]["large_amount_bdt"] and first_time:
        hits.append({"id": "RULE-BASIC", "type": "business_rule", "text": "Basic rule: large amount to a new receiver"})
    return hits


@router.get("/customers/{customer_id}/profile")
def profile(customer_id: str, request: Request, user: dict = Depends(require("customer", "ops"))) -> dict:
    own(user, customer_id)
    s = engines()
    cust = s.world.customers.set_index("customer_id")
    if customer_id not in cust.index:
        raise HTTPException(404, "Unknown customer")
    ev = s.world.events
    mine = ev[(ev["src"] == customer_id) | (ev["dst"] == customer_id)].tail(10).iloc[::-1]
    tx = [{"time": str(r.ts), "type": str(r.etype), "direction": "out" if r.src == customer_id else "in",
           "counterparty": r.dst if r.src == customer_id else r.src, "amount": float(r.amount)} for r in mine.itertuples()]
    c = cust.loc[customer_id]
    persona = next((p for p in s.demo["personas"].values() if p["id"] == customer_id), None)
    return envelope(request, {"customer_id": customer_id, "display_name": persona["name"] if persona else customer_id,
                              "zone": c["zone"], "channel": c["channel"], "language": c["language"],
                              "tenure_days": int(s.world.n_days - c["registration_day"]), "balance_bdt": float(s.pause.bal[int(customer_id[1:])]),
                              "today": str((START + pd.Timedelta(days=s.world.n_days)).date()), "recent": tx})


@router.post("/pause-check")
def pause_check(body: PauseIn, request: Request, user: dict = Depends(require("customer", "ops"))) -> dict:
    own(user, body.sender_id)
    if body.sender_id == body.recipient_wallet:
        raise HTTPException(422, "Sender and receiver must be different")
    s = engines()
    ctx = body.simulated_context.model_dump(exclude_none=True) if body.simulated_context else {}
    try:
        r = s.pause.check(body.sender_id, body.recipient_wallet, body.amount, hour=body.hour, channel=body.channel, **ctx)
    except (IndexError, ValueError) as e:
        raise HTTPException(404, "Unknown wallet") from e
    except Exception:  # noqa: BLE001 - never fail the customer: fall back to the transparent rule
        telemetry.inc("pause_degraded")
        first = True
        hits = _rule_hits(body.amount, first)
        return envelope(request, {"risk_level": "medium" if hits else "low", "state": "basic_check_only", "reasons": [],
                                  "rule_hits": hits, "recommendation": ["verify_number", "continue_anyway"], "human_review": "not_needed"},
                        "rule-baseline", degraded=True, reason="model unavailable: basic check only")
    text = s.text.check(body.note) if body.note else None
    brief = s.briefs.for_transfer(r, body.amount, body.note)
    telemetry.inc(f"pause_state:{r['state']}")
    feats = r.pop("features")
    body_out = {**r, "rule_hits": _rule_hits(body.amount, bool(feats["first_time_pair"])), "note_check": text,
                "brief": {k: v for k, v in brief.items() if k != "evidence_object"},
                "evidence_ids": [x["id"] for x in brief["evidence_object"]["reasons"]],
                "inputs": {"amount": body.amount, "hour": body.hour, "channel": body.channel, "simulated_context": ctx or None},
                "key_facts": {"recipient_age_days": feats["recipient_age_days"], "first_time_pair": bool(feats["first_time_pair"]),
                              "receiver_senders_7d": feats["recipient_sender_days_7d"], "share_of_balance": feats["amount_to_balance"]}}
    return envelope(request, body_out, r["model_version"])


@router.post("/text-check")
def text_check(body: TextIn, request: Request, user: dict = Depends(require("customer", "ops"))) -> dict:
    s = engines()
    r = s.text.check(body.text)
    telemetry.inc(f"text_state:{r['state']}")
    return envelope(request, r, r["model_version"])


@router.get("/customers/{customer_id}/cashflow")
def cashflow(customer_id: str, request: Request, goal_bdt: float | None = None, months: int | None = None,
             user: dict = Depends(require("customer", "ops"))) -> dict:
    own(user, customer_id)
    s = engines()
    if goal_bdt is not None and not (100 <= goal_bdt <= 10_000_000):
        raise HTTPException(422, "Goal must be between Tk 100 and Tk 10,000,000")
    if months is not None and not (1 <= months <= 60):
        raise HTTPException(422, "Months must be between 1 and 60")
    try:
        r = s.forecasts.customer(customer_id, goal_bdt, months)
    except KeyError as e:
        raise HTTPException(404, "Unknown customer") from e
    return envelope(request, r, "ai3-" + r["model"])
