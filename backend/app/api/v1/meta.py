"""Demo login, personas/scenarios, model metadata, homepage world sample and the Trust Center summary."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from uvera_ml.common import repo_root
from uvera_ml.eval.report import AIS, fairness_summary, headline, served_text_by_language

from app.api.v1.deps import engines, envelope
from app.core.security import issue
from app.core.telemetry import telemetry
from app.state import state

router = APIRouter(tags=["meta"])


@lru_cache(maxsize=1)
def _served_text_by_language() -> dict | None:
    """Per-language results of the text model the API actually serves (scored once on the held-out style)."""
    out = served_text_by_language(repo_root())
    return {k: v for k, v in out.items() if k not in ("model", "overall")} if out else None


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["customer", "agent", "ops"]
    subject_id: str | None = None


@router.post("/auth/demo-login")
def demo_login(body: LoginIn) -> dict:
    s = engines()
    p = s.demo["personas"]
    default = {"customer": p["customer"]["id"], "agent": p["agent"]["id"], "ops": p["ops"]["id"]}[body.role]
    subject = body.subject_id or default
    if body.role == "customer" and subject not in set(s.world.customers["customer_id"]):
        raise HTTPException(404, "Unknown customer")
    if body.role == "agent" and subject not in set(s.world.agents["agent_id"]):
        raise HTTPException(404, "Unknown agent")
    name = next((v["name"] for v in p.values() if v["id"] == subject), None)
    return {"token": issue(body.role, subject), "role": body.role, "subject_id": subject, "display_name": name or subject,
            "note": "Demo login for synthetic personas only."}


@router.get("/demo")
def demo(request: Request) -> dict:
    s = engines()
    return envelope(request, {"personas": s.demo["personas"], "scenarios": s.demo["scenarios"]})


@router.get("/meta")
def meta(request: Request) -> dict:
    s = engines()
    w = s.world.meta
    return envelope(request, {
        "world": {k: w[k] for k in ("scale", "seed", "days", "n_events", "n_scam_transfers", "n_mules", "n_disguised_merchants")},
        "models": {"ai1": s.pause.version, "ai2": s.text.version, "ai3": s.forecasts.source["ai3"], "ai4": s.forecasts.source["ai4"],
                   "ai5": s.qr.version, "ai6": s.cases.source, "ai7": s.briefs.mode},
        "artifact_sources": {ai: s.store.source_of(ai) for ai in ("ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7")},
    })


@router.get("/web/world-sample")
def world_sample() -> dict:
    s = engines()
    data = s.store.json("artifacts/web/world_sample.json")
    if not data:
        raise HTTPException(404, "World sample not built yet")
    return data


@router.get("/metrics/summary")
def metrics_summary(request: Request) -> dict:
    s = engines()
    per_ai = {k: s.store.json(f"reports/metrics_{k}.json", None) for k in AIS}
    found = {k: v for k, v in per_ai.items() if v}
    if "ai2" in found and s.store.source_of("ai2") == "official" and (by_lang := _served_text_by_language()):
        found["ai2"] = {**found["ai2"], "served_by_language": by_lang}
    # Built per AI from the newest available file (official Kaggle run first), so official and dev never mix in one number.
    summary = {"available": {AIS[k]: k in found for k in AIS}, "headline": headline(found), "fairness": fairness_summary(found),
               "note": "All results are on synthetic data: they show that the pipeline works, not real-world accuracy."}
    data_card = s.store.json("reports/data_card_stats.json", None)
    return envelope(request, {
        "summary": summary, "per_ai": per_ai, "data_card": data_card,
        "sources": {ai: s.store.source_of(ai) for ai in ("ai1", "ai2", "ai3", "ai4", "ai5", "ai6", "ai7")},
        "live_health": {**telemetry.summary(), "briefs": s.briefs.stats},
        "note": "Every number here is read from files written by the notebooks. Results are on synthetic data.",
    })


@router.get("/health/startup")
def startup() -> dict:
    return {"ready": state.ready, "progress": state.progress, "error": state.error}
