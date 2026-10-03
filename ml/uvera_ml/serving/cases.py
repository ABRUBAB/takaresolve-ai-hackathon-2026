"""AI-6 case queue + case detail with the evidence graph and the Dispute Clock (business rules, not AI)."""
from __future__ import annotations

import pandas as pd

from uvera_ml.common import load_config
from uvera_ml.graph.linker import tidy_plurals
from uvera_ml.serving.store import ArtifactStore
from uvera_ml.sim.world import DAY, START

CLOCKS_FOR_CASE = [
    ("issuer_accept_or_reject", "Accept or reject the complaint"),
    ("suspected_fraud_investigation", "Finish the fraud investigation"),
    ("reimbursement_if_institution_fault", "Repay if the provider was at fault"),
]
CLOCKS_IF_QR = [("acquirer_response", "Merchant's bank must respond")]


def _add(start_t: int, limit: int, unit: str) -> int:
    if unit == "minutes":
        return start_t + limit * 60
    if unit in ("working_days", "business_days"):  # Bangladesh weekend: Friday + Saturday
        t, left = start_t, limit
        while left > 0:
            t += DAY
            if (START + pd.Timedelta(seconds=t)).dayofweek not in (4, 5):
                left -= 1
        return t
    return start_t + limit * DAY


class CaseEngine:
    def __init__(self, store: ArtifactStore, qr_state=None):
        self.cases = store.json("artifacts/ai6/cases.json", []) or []
        self.by_key = {c["case_key"]: c for c in self.cases}
        self.source = store.source_of("ai6")
        self.rules = load_config("rules/dispute")
        self.qr_state = qr_state or (lambda m: None)
        # demo clock: 'now' is 6 hours after the newest case opened, so recent cases are fresh and older ones show urgency
        for c in self.cases:  # the clock starts when the latest victim complaint arrives
            for e in c.get("evidence", []):
                e["text"] = tidy_plurals(e["text"])
            c["complaint_t"] = max((e["t"] for e in c["edges"] if e["hop"] == 0), default=c["opened_at_t"])
        self.now_t = (max(c["complaint_t"] for c in self.cases) + 6 * 3600) if self.cases else 0

    def clock(self, case: dict) -> list[dict]:
        items = CLOCKS_FOR_CASE + (CLOCKS_IF_QR if case.get("merchants") else [])
        out = []
        for key, label in items:
            rule = self.rules["clocks"].get(key)
            if not rule:
                continue
            start = case["complaint_t"]
            due = _add(start, int(rule["limit"]), rule["unit"])
            frac = (due - self.now_t) / max(due - start, 1)
            out.append({"rule": key, "label": label, "limit": rule["limit"], "unit": rule["unit"],
                        "due": str(START + pd.Timedelta(seconds=due)), "remaining_hours": round((due - self.now_t) / 3600, 1),
                        "remaining_fraction": round(max(frac, 0.0), 3),
                        "status": "breached" if frac < 0 else "urgent" if frac < self.rules.get("warn_when_remaining_fraction", 0.25) else "ok"})
        return out

    def _summary(self, c: dict) -> dict:
        clock = self.clock(c)
        nxt = min((x for x in clock if x["status"] != "breached"), key=lambda x: x["remaining_hours"], default=None)
        urgency = 1.0 if any(x["status"] == "urgent" for x in clock) else 0.5 if nxt and nxt["remaining_hours"] < 48 else 0.0
        return {"case_key": c["case_key"], "score": c["score"], "n_alerts": c["n_alerts"], "victims": len(c["victims"]),
                "wallets": len(c["wallets"]), "merchants": len(c["merchants"]), "agents": len(c["agents"]),
                "amount_at_risk_bdt": c["amount_at_risk_bdt"], "qr_flagged_endpoint": c["qr_flagged_endpoint"],
                "opened": str(START + pd.Timedelta(seconds=c["opened_at_t"])),
                "opened_hours_ago": round((self.now_t - c["opened_at_t"]) / 3600, 1),
                "latest_complaint": str(START + pd.Timedelta(seconds=c["complaint_t"])),
                "latest_complaint_hours_ago": round((self.now_t - c["complaint_t"]) / 3600, 1),
                "next_deadline": nxt, "breached": sum(x["status"] == "breached" for x in clock),
                "priority": round(c["score"] * (1 + urgency), 4)}

    def queue(self, limit: int = 50, statuses: dict | None = None) -> list[dict]:
        rows = [self._summary(c) | {"status": (statuses or {}).get(c["case_key"], "open")} for c in self.cases]
        return sorted(rows, key=lambda r: -r["priority"])[:limit]

    def graph(self, c: dict) -> dict:
        victims, wallets = set(c["victims"]), set(c["wallets"])
        nodes, seen = [], set()

        def node(nid):
            if nid in seen:
                return
            seen.add(nid)
            kind = {"C": "wallet", "A": "agent", "M": "merchant"}.get(nid[0], "other")
            role = "victim" if nid in victims else "mule_suspect" if nid in wallets else kind
            flag = self.qr_state(nid) if kind == "merchant" else None
            nodes.append({"id": nid, "type": kind, "role": role, "qr_state": flag})

        edges = []
        for e in c["edges"]:
            node(e["src"])
            node(e["dst"])
            edges.append({"id": f"e{e['event_id']}", "source": e["src"], "target": e["dst"], "type": e["etype"],
                          "amount": e["amount"], "hop": e["hop"], "time": str(START + pd.Timedelta(seconds=e["t"]))})
        return {"nodes": nodes, "edges": edges}

    def detail(self, key: str) -> dict:
        c = self.by_key[key]
        return {**self._summary(c), "evidence": c["evidence"], "victim_ids": c["victims"], "wallet_ids": c["wallets"],
                "merchant_ids": c["merchants"], "agent_ids": c["agents"], "forwarded_share": c["forwarded_share"],
                "graph": self.graph(c), "dispute_clock": self.clock(c),
                "dispute_rules_verified": bool(self.rules.get("verified", False)),
                "dispute_rules_note": "Deadlines follow Bangladesh Bank's Bangla QR dispute guideline (issued 27 Sep 2026, effective "
                                      "1 Dec 2026) as reported by The Daily Star and The Business Standard; all eight limits match "
                                      "both reports. The circular's own text was not checked."}
