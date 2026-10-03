"""AI-6 Case Linker: turn many alerts into a few evidence-backed cases.

From every risky transfer (AI-1), follow the money forward in time (time-respecting paths, <= 3 hops, <= 48 h)
through wallets to cash-out points (agents) and QR merchants (scored by AI-5). Alerts that share a downstream
wallet are merged into one case. The evidence subgraph IS the explanation shown to the analyst.
"""
from __future__ import annotations

import json
import re
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from uvera_ml.common import write_json

MAX_HOPS, WINDOW_S = 3, 48 * 3600


def tidy_plurals(text: str) -> str:
    """'1 customer(s)' -> '1 customer', '109 customer(s)' -> '109 customers' (evidence lines are shown to analysts)."""
    return re.sub(r"(\d[\d,]*)([^\d(]*?)(\w+)\(s\)", lambda m: m[1] + m[2] + m[3] + ("" if m[1] == "1" else "s"), text)


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def _adjacency(ev: pd.DataFrame) -> dict:
    keep = ev[(ev["src_kind"] == 0) & ev["etype"].isin(["p2p", "qr_pay", "cash_out"])].sort_values("t")
    adj = defaultdict(lambda: {"t": [], "dst": [], "etype": [], "amount": [], "event_id": [], "case_id": []})
    for row in keep[["src", "t", "dst", "etype", "amount", "event_id", "case_id"]].itertuples(index=False):
        a = adj[row.src]
        a["t"].append(row.t)
        a["dst"].append(row.dst)
        a["etype"].append(str(row.etype))
        a["amount"].append(float(row.amount))
        a["event_id"].append(int(row.event_id))
        a["case_id"].append(int(row.case_id))
    return adj


def trace(adj: dict, start: str, t0: int) -> list[dict]:
    """Time-respecting forward paths from `start` after time t0."""
    edges, frontier = [], [(start, t0, 0)]
    seen = set()
    while frontier:
        node, t, hop = frontier.pop()
        if hop >= MAX_HOPS or node not in adj:
            continue
        a = adj[node]
        i = bisect_left(a["t"], t)
        while i < len(a["t"]) and a["t"][i] <= t0 + WINDOW_S:
            e = {"src": node, "dst": a["dst"][i], "t": a["t"][i], "etype": a["etype"][i], "amount": a["amount"][i],
                 "event_id": a["event_id"][i], "true_case_id": a["case_id"][i], "hop": hop + 1}
            if e["event_id"] not in seen:
                seen.add(e["event_id"])
                edges.append(e)
                if e["etype"] == "p2p":
                    frontier.append((e["dst"], e["t"], hop + 1))
            i += 1
    return edges


def link_cases(world, scored_transfers: pd.DataFrame, merchant_scores: pd.DataFrame | None = None) -> tuple[list[dict], dict]:
    alerts = scored_transfers[(scored_transfers["risk_level"] == "high") |
                              ((scored_transfers["unsure"]) & (scored_transfers["risk_level"] != "low"))].copy()
    t_min = int(alerts["t"].min()) if len(alerts) else 0
    ev = world.events[world.events["t"] >= t_min - 3600]
    adj = _adjacency(ev)
    flagged_merchants = set()
    if merchant_scores is not None and len(merchant_scores):
        flagged_merchants = set(merchant_scores.loc[merchant_scores["state"] != "green", "merchant_id"])

    uf, paths = _UF(), {}
    for a in alerts.itertuples(index=False):
        first = {"src": a.src, "dst": a.dst, "t": int(a.t), "etype": "p2p", "amount": float(a.amount), "event_id": int(a.event_id),
                 "true_case_id": int(a.case_id), "hop": 0}
        e = [first] + trace(adj, a.dst, int(a.t))
        paths[int(a.event_id)] = e
        uf.union(("alert", int(a.event_id)), ("wallet", a.dst))
        for x in e:
            if x["etype"] == "p2p":
                uf.union(("alert", int(a.event_id)), ("wallet", x["dst"]))

    groups = defaultdict(list)
    for a in alerts.itertuples(index=False):
        groups[uf.find(("alert", int(a.event_id)))].append(a)

    cases = []
    for gi, members in enumerate(groups.values()):
        edges = {x["event_id"]: x for m in members for x in paths[int(m.event_id)]}.values()
        edges = sorted(edges, key=lambda x: x["t"])
        victims = sorted({m.src for m in members})
        wallets = sorted({x["dst"] for x in edges if x["etype"] == "p2p"} - set(victims))
        merchants = sorted({x["dst"] for x in edges if x["etype"] == "qr_pay"})
        agents = sorted({x["dst"] for x in edges if x["etype"] == "cash_out"})
        received = sum(float(m.amount) for m in members)
        forwarded = sum(x["amount"] for x in edges if x["hop"] >= 1)
        fwd_share = min(1.0, forwarded / max(received, 1.0))
        pmax = float(max(m.p_calibrated for m in members))
        n_flagged = sum(mm in flagged_merchants for mm in merchants)
        qr_flag = n_flagged > 0
        # transparent chain score (weights are design assumptions, shown to the analyst)
        score = 1 - (1 - pmax) * (1 - 0.15 * min(len(victims) - 1, 3)) * (1 - 0.5 * fwd_share) * (1 - (0.3 if qr_flag else 0))
        evidence = [
            {"id": "E1", "type": "model", "text": f"Highest AI-1 scam probability among linked transfers: {pmax:.2f}", "value": pmax},
            {"id": "E2", "type": "model", "text": f"{len(victims)} customer(s) sent money into the same wallet chain", "value": len(victims)},
            {"id": "E3", "type": "model", "text": f"{fwd_share:.0%} of the money moved on within 48 hours", "value": fwd_share},
        ]
        if merchants:
            evidence.append({"id": "E4", "type": "model" if qr_flag else "rule",
                             "text": f"Money reached {len(merchants)} QR merchant(s)"
                                     + (f"; {n_flagged} of them flagged by QR Shield" if qr_flag else ""),
                             "value": n_flagged if qr_flag else len(merchants)})
        if agents:
            evidence.append({"id": "E5", "type": "rule", "text": f"Cash-out at {len(agents)} agent point(s)", "value": len(agents)})
        for e in evidence:
            e["text"] = tidy_plurals(e["text"])
        cases.append({
            "case_key": f"CASE-{gi + 1:04d}", "score": round(float(score), 4), "n_alerts": len(members),
            "victims": victims, "wallets": wallets, "merchants": merchants, "agents": agents,
            "amount_at_risk_bdt": round(received, 2), "forwarded_share": round(fwd_share, 4), "qr_flagged_endpoint": qr_flag,
            "opened_at_t": int(min(m.t for m in members)), "alert_event_ids": [int(m.event_id) for m in members],
            "edges": [{k: v for k, v in x.items() if k != "true_case_id"} for x in edges], "evidence": evidence,
            "_true_case_ids": sorted({int(m.case_id) for m in members if int(m.case_id) >= 0}),
            "_true_scam_alerts": int(sum(int(m.is_scam) for m in members)),
        })
    cases.sort(key=lambda c: -c["score"])
    return cases, {"alerts": int(len(alerts)), "true_scam_alerts": int(alerts["is_scam"].sum()), "events_in_graph": int(len(ev))}


def evaluate_linking(world, cases: list[dict]) -> dict:
    truth = world.truth_cases.set_index("case_id")["mule"].to_dict()
    # pairs of true-scam alerts paid to the same mule: are they in the same linked case?
    alert_case, alert_mule = {}, {}
    for c in cases:
        for eid in c["alert_event_ids"]:
            alert_case[eid] = c["case_key"]
    ev = world.events.set_index("event_id")
    for eid in alert_case:
        cid = int(ev.at[eid, "case_id"])
        if cid >= 0 and int(ev.at[eid, "is_scam"]) == 1:
            alert_mule[eid] = truth.get(cid)
    by_mule = defaultdict(list)
    for eid, mule in alert_mule.items():
        by_mule[mule].append(eid)
    same = total = 0
    for eids in by_mule.values():
        for i in range(len(eids)):
            for j in range(i + 1, len(eids)):
                total += 1
                same += alert_case[eids[i]] == alert_case[eids[j]]
    purities = []
    for c in cases:
        mules = [alert_mule[e] for e in c["alert_event_ids"] if e in alert_mule]
        if len(mules) >= 1:
            purities.append(pd.Series(mules).value_counts().iloc[0] / len(c["alert_event_ids"]))
    true_cashouts = world.events[(world.events["mule_flow"] == 1) & world.events["etype"].isin(["cash_out", "qr_pay"])]
    found = {x["event_id"] for c in cases for x in c["edges"]}
    window = true_cashouts[true_cashouts["t"] >= min((c["opened_at_t"] for c in cases), default=0)]
    reached_cases = window[window["case_id"].isin({cid for c in cases for cid in c["_true_case_ids"]})]
    ranked = sorted(cases, key=lambda c: -c["score"])
    n_true = sum(c["_true_scam_alerts"] for c in cases)
    return {"n_cases": len(cases), "n_alerts": int(sum(c["n_alerts"] for c in cases)),
            "alerts_per_case": float(np.mean([c["n_alerts"] for c in cases])) if cases else None,
            "analyst_items_reduction": 1 - len(cases) / max(1, sum(c["n_alerts"] for c in cases)),
            "same_mule_pairs_linked": same / total if total else None, "same_mule_pairs": total,
            "case_purity_mean": float(np.mean(purities)) if purities else None,
            "cashouts_found_for_detected_cases": float(reached_cases["event_id"].isin(found).mean()) if len(reached_cases) else None,
            "cases_with_true_scam": int(sum(c["_true_scam_alerts"] > 0 for c in cases)),
            # cases are sorted by chain score: how much of the real scam reaches the top of the analyst queue?
            "real_scam_alerts_in_top_cases": {str(k): float(sum(c["_true_scam_alerts"] for c in ranked[:k]) / max(1, n_true))
                                              for k in (5, 10, 20)},
            "top_cases_with_real_scam": {str(k): int(sum(c["_true_scam_alerts"] > 0 for c in ranked[:k])) for k in (5, 10, 20)}}


def communities(cases: list[dict]) -> dict:
    g = nx.Graph()
    for c in cases:
        for x in c["edges"]:
            g.add_edge(x["src"], x["dst"], weight=x["amount"])
    if g.number_of_edges() == 0:
        return {"n_nodes": 0, "n_communities": 0}
    comms = nx.community.louvain_communities(g, weight="weight", seed=42)
    return {"n_nodes": g.number_of_nodes(), "n_edges": g.number_of_edges(), "n_communities": len(comms),
            "largest_community": max(len(c) for c in comms)}


def run_ai6(world, out: str | Path, scored_transfers: pd.DataFrame, merchant_scores: pd.DataFrame | None, top_n: int = 300) -> dict:
    out = Path(out)
    art, rep = out / "artifacts" / "ai6", out / "reports"
    art.mkdir(parents=True, exist_ok=True)
    rep.mkdir(parents=True, exist_ok=True)
    cases, info = link_cases(world, scored_transfers, merchant_scores)
    metrics = evaluate_linking(world, cases)
    summary = {"ai": "AI-6 Case Linker", "method": "time-respecting path tracing (<=3 hops, <=48h) + union-find linking + "
               "transparent chain score; Louvain communities for ring discovery",
               "inputs": info, "linking": metrics, "communities": communities(cases),
               "score_formula": "1 - (1-p_max)(1-0.15*min(victims-1,3))(1-0.5*forwarded_share)(1-0.3*qr_flagged)"}
    public = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cases[:top_n]]
    (art / "cases.json").write_text(json.dumps(public, ensure_ascii=False, default=float), encoding="utf-8")
    write_json(rep / "metrics_ai6.json", summary)
    return summary
