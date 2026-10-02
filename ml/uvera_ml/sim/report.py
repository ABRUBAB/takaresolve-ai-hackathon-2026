"""NB00 helpers: data-card statistics and the small network sample used by the homepage 3D "Trust Field"."""
from __future__ import annotations

import numpy as np
import pandas as pd

from uvera_ml.sim.world import World


def world_stats(w: World) -> dict:
    ev = w.events
    p2p = ev[(ev["etype"] == "p2p") & (ev["mule_flow"] == 0)]
    return {
        "meta": w.meta,
        "entities": {"customers": len(w.customers), "agents": len(w.agents), "merchants": len(w.merchants)},
        "events_by_type": ev["etype"].astype(str).value_counts().to_dict(),
        "p2p_scam_rate": float(p2p["is_scam"].mean()),
        "scams_by_family": p2p.loc[p2p["is_scam"] == 1, "scam_family"].value_counts().to_dict(),
        "label_noise": {"scam_labels_lost": int(((p2p["is_scam"] == 1) & (p2p["label_scam"] == 0)).sum()),
                        "false_reports": int(((p2p["is_scam"] == 0) & (p2p["label_scam"] == 1)).sum())},
        "qr_disguise_payments_by_family": ev["qr_family"].value_counts().to_dict(),
        "disguised_merchants_by_family": w.truth_merchants["family"].value_counts().to_dict(),
        "mule_wallets": int(w.truth_customers["is_mule"].sum()), "cases": int(len(w.truth_cases)),
        "customers_by_zone": w.customers["zone"].value_counts().to_dict(),
        "customers_by_channel": w.customers["channel"].value_counts().to_dict(),
        "customers_by_language": w.customers["language"].value_counts().to_dict(),
        "amount_quantiles_p2p": p2p["amount"].quantile([0.1, 0.5, 0.9, 0.99]).round(0).to_dict(),
    }


def web_sample(w: World, n_customers: int = 500, seed: int = 7) -> dict:
    """~800 nodes / ~2,000 edges for the homepage: 3 layers = customer, agent & merchant, operations (cases)."""
    rng = np.random.default_rng(seed)
    ev = w.events
    scam = ev[ev["is_scam"] == 1]
    focus_cases = scam["case_id"].drop_duplicates().head(12).tolist()
    chain = ev[ev["case_id"].isin(focus_cases)]
    custs = set(chain["src"]) | set(chain.loc[chain["dst_kind"] == 0, "dst"])
    custs |= set(rng.choice(w.customers["customer_id"], n_customers, replace=False))
    sub = ev[ev["src"].isin(custs) & ev["etype"].isin(["p2p", "qr_pay", "cash_out"])]
    sub = pd.concat([sub.sample(min(1800, len(sub)), random_state=seed), chain[chain["etype"].isin(["p2p", "qr_pay", "cash_out"])]])
    sub = sub.drop_duplicates("event_id")
    nodes = {}
    for col, kind_col in (("src", "src_kind"), ("dst", "dst_kind")):
        for nid, k in zip(sub[col], sub[kind_col]):
            nodes[nid] = {0: "customer", 1: "agent", 2: "merchant"}.get(int(k), "external")
    mules = set(w.truth_customers.loc[w.truth_customers["is_mule"], "customer_id"])
    disguised = set(w.truth_merchants.loc[w.truth_merchants["is_disguised"], "merchant_id"])
    out_nodes = [{"id": n, "type": t, "layer": 0 if t == "customer" else 1,
                  "flag": "mule" if n in mules else "disguised_qr" if n in disguised else None} for n, t in nodes.items()]
    for c in focus_cases:  # the operations layer: one node per linked case
        out_nodes.append({"id": f"CASE-{c}", "type": "case", "layer": 2, "flag": "case"})
    edges = [{"source": s, "target": d, "type": str(e), "amount": float(a), "scam": bool(sc), "case": int(cid) if cid >= 0 else None}
             for s, d, e, a, sc, cid in zip(sub["src"], sub["dst"], sub["etype"], sub["amount"], sub["is_scam"], sub["case_id"])]
    for c in focus_cases:
        victim = scam.loc[scam["case_id"] == c, "src"].iloc[0]
        edges.append({"source": victim, "target": f"CASE-{c}", "type": "case_link", "amount": 0.0, "scam": True, "case": int(c)})
    return {"note": "Synthetic sample from UVERA-World for the homepage visual. Layers: 0 customers, 1 agents & merchants, 2 cases.",
            "nodes": out_nodes, "edges": edges}
