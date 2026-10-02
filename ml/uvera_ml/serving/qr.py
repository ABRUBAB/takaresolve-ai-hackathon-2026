"""AI-5 live QR Shield views: operations watchlist, merchant detail, agent-zone summary. Ground truth is never exposed."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from uvera_ml.common import load_config
from uvera_ml.serving.store import ArtifactStore
from uvera_ml.sim.world import World

TRUTH_COLS = ["is_disguised", "family"]
ACTIONS = {
    "green": ["no action"],
    "amber": ["add to watchlist", "ask the merchant for sale evidence"],
    "red": ["ask the merchant for sale evidence", "propose a temporary QR limit (a person must approve)"],
    "grey_review": ["human review: the evidence is mixed"],
}


class QREngine:
    def __init__(self, world: World, store: ArtifactStore):
        self.w = world
        self.source = store.source_of("ai5")
        scores = store.parquet("artifacts/ai5/merchant_scores.parquet")
        self.fee = load_config("qr_fee")
        if scores is None:
            self.scores = pd.DataFrame(columns=["merchant_id", "week", "state", "p_calibrated"])
        else:
            self.scores = scores.drop(columns=[c for c in TRUTH_COLS if c in scores.columns])
        self.latest = (self.scores.sort_values("week").groupby("merchant_id").tail(1).set_index("merchant_id")
                       if len(self.scores) else self.scores)
        zs = store.parquet("artifacts/ai5/zone_summary.parquet")
        self.zones = zs if zs is not None else pd.DataFrame(columns=["zone", "week", "flagged_merchants", "est_fee_leakage_bdt"])
        self._features = None
        self.version = f"ai5-qr-shield-{self.source}"

    def state_of(self, merchant_id: str) -> str | None:
        return None if merchant_id not in self.latest.index else str(self.latest.loc[merchant_id, "state"])

    def watchlist(self, state: str | None = None, limit: int = 50) -> list[dict]:
        df = self.latest.reset_index()
        if state:
            df = df[df["state"] == state]
        order = {"red": 0, "grey_review": 1, "amber": 2, "green": 3}
        df = df.assign(_o=df["state"].map(order)).sort_values(["_o", "p_calibrated"], ascending=[True, False]).head(limit)
        return [self._row(r) for r in df.to_dict("records")]

    def _row(self, r: dict) -> dict:
        reasons = json.loads(r["reasons"]) if isinstance(r.get("reasons"), str) else []
        return {"merchant_id": r["merchant_id"], "zone": r["zone"], "category": r["category"], "size": r["size"],
                "week": int(r["week"]), "state": r["state"], "p_calibrated": float(r["p_calibrated"]),
                "payments": int(r["n_payments"]), "volume_bdt": float(r["volume"]),
                "est_fee_leakage_bdt": float(r.get("est_fee_leakage_bdt", 0.0)),
                "components": {k.replace("component_", ""): float(r[k]) for k in r if str(k).startswith("component_")},
                "reasons": reasons, "recommended_actions": ACTIONS.get(r["state"], [])}

    def features(self) -> pd.DataFrame:
        if self._features is None:
            from uvera_ml.features.qr import build_qr_features

            self._features = build_qr_features(self.w).drop(columns=TRUTH_COLS, errors="ignore")
        return self._features

    def merchant(self, merchant_id: str) -> dict:
        if merchant_id not in self.latest.index:
            raise KeyError(merchant_id)
        row = self._row({**self.latest.loc[merchant_id].to_dict(), "merchant_id": merchant_id})
        hist = self.scores[self.scores["merchant_id"] == merchant_id].sort_values("week")
        f = self.features()
        mine = f[(f["merchant_id"] == merchant_id) & (f["week"] == row["week"])]
        coarse = f[(f["category"] == row["category"]) & (f["zone"] == row["zone"]) & (f["week"] == row["week"])]
        fine = coarse[coarse["size"] == row["size"]] if "size" in coarse.columns else coarse
        peers = fine if len(fine) >= 5 else coarse  # same type, area and size when there are enough shops (as in the model)
        compare = []
        for col, label in [("round_share", "Round-amount payments"), ("one_time_payer_share", "One-time payers"),
                           ("cashin_gap_share", "Paid minutes after a cash-in"), ("burst_share", "Quick repeat payments"),
                           ("median_ticket", "Typical payment (Tk)"), ("n_payers", "Different payers per week")]:
            if len(mine):
                compare.append({"metric": label, "this_shop": float(mine[col].iloc[0]),
                                "peer_median": float(peers[col].median()), "peer_p90": float(peers[col].quantile(0.9))})
        return {**row, "model_version": self.version,
                "history": [{"week": int(r.week), "state": r.state, "p_calibrated": float(r.p_calibrated)} for r in hist.itertuples()],
                "peer_comparison": compare, "peers_n": int(len(peers)),
                "fee_assumption": {"fee_rate": self.fee.get("fee_rate"), "verified": self.fee.get("verified", False),
                                   "note": self.fee.get("note")}}

    def zone(self, zone: str) -> dict:
        z = self.zones[self.zones["zone"] == zone].sort_values("week")
        latest = z.tail(1).to_dict("records")
        return {"zone": zone, "weeks": [{"week": int(r.week), "flagged_merchants": int(r.flagged_merchants),
                                         "est_fee_leakage_bdt": float(r.est_fee_leakage_bdt)} for r in z.itertuples()],
                "latest": latest[0] if latest else None,
                "note": "Zone-level only: agents never see which customers or shops are flagged."}

    def counts(self) -> dict:
        if not len(self.latest):
            return {}
        return {k: int(v) for k, v in self.latest["state"].value_counts().items()} | {
            "est_fee_leakage_bdt": float(np.nansum(self.latest.get("est_fee_leakage_bdt", pd.Series(dtype=float))))}
