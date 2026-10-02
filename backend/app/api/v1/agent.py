"""Agent area: Liquidity Copilot (AI-4) and own activity vs peers + zone-level QR leakage (AI-5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.deps import engines, envelope
from app.core.security import own, require

router = APIRouter(tags=["agent"])


@router.get("/agents/{agent_id}/liquidity")
def liquidity(agent_id: str, request: Request, user: dict = Depends(require("agent", "ops"))) -> dict:
    own(user, agent_id)
    s = engines()
    try:
        r = s.forecasts.agent(agent_id)
    except KeyError as e:
        raise HTTPException(404, "Unknown agent") from e
    persona = next((p for p in s.demo["personas"].values() if p["id"] == agent_id), None)
    return envelope(request, {**r, "display_name": persona["name"] if persona else agent_id}, "ai4-" + r["model"])


@router.get("/agents/{agent_id}/area")
def area(agent_id: str, request: Request, user: dict = Depends(require("agent", "ops"))) -> dict:
    own(user, agent_id)
    s = engines()
    agents = s.world.agents.set_index("agent_id")
    if agent_id not in agents.index:
        raise HTTPException(404, "Unknown agent")
    zone = agents.loc[agent_id, "zone"]
    return envelope(request, {"agent_id": agent_id, "zone": zone, "qr": s.qr.zone(zone),
                              "peers": s.forecasts.agent(agent_id)["peers"]}, s.qr.version)
