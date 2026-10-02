"""AI-1 live Pause Check: features for a NEW draft transfer at 'now' (the day after the simulation ends)."""
from __future__ import annotations

import math

import lightgbm as lgb
import numpy as np
import pandas as pd

from uvera_ml.common import load_config
from uvera_ml.features.ai1 import FEATURES, dense_state
from uvera_ml.policy import decide
from uvera_ml.serving.store import ArtifactStore
from uvera_ml.sim.world import DAY, START, World
from uvera_ml.uncertainty.calibration import IsotonicCalibrator
from uvera_ml.uncertainty.conformal import MondrianConformal
from uvera_ml.uncertainty.novelty import RobustNovelty
from uvera_ml.xai.reasons import top_reasons


def cidx(cid: str) -> int:
    return int(str(cid)[1:])


class PauseCheckEngine:
    def __init__(self, world: World, store: ArtifactStore):
        self.w, self.store = world, store
        self.booster = lgb.Booster(model_file=str(store.path("artifacts/ai1/model.txt")))
        self.calib = IsotonicCalibrator.from_json(store.json("artifacts/ai1/calibrator.json"))
        self.conf = MondrianConformal.from_json(store.json("artifacts/ai1/conformal.json"))
        self.nov = RobustNovelty.from_json(store.json("artifacts/ai1/novelty.json"))
        self.thr = store.json("artifacts/ai1/thresholds.json")
        self.rules = load_config("rules/actions")
        self.source = store.source_of("ai1")
        S = dense_state(world)
        D = self.D = S["D"]
        self.reg, self.pairs, self.bal = S["reg"], S["pairs"], S["bal_end"]
        w7 = slice(max(0, D - 7), D)
        w30 = slice(max(0, D - 30), D)
        self.out7 = S["out_cnt"][w7].sum(0)
        self.in7 = S["in_cnt"][w7].sum(0)
        self.sdays7 = S["sender_days"][w7].sum(0)
        self.inamt7 = S["in_amt_all"][w7].sum(0)
        self.outamt7 = S["out_amt_all"][w7].sum(0)
        self.cash7 = S["cashout"][w7].sum(0)
        self.c30, self.s30, self.q30 = S["p2p_cnt"][w30].sum(0), S["p2p_sum"][w30].sum(0), S["p2p_sq"][w30].sum(0)
        ev = world.events
        inflow = ev[(ev["dst_kind"] == 0) & ev["etype"].isin(["cash_in", "salary_in", "remit_in", "p2p"])]
        self.last_in = inflow.groupby("dst")["t"].max().to_dict()
        sec = world.security
        self.last_dev = sec[sec["kind"] == "device_change"].groupby("customer_id")["t"].max().to_dict()
        self.last_pin = sec[sec["kind"] == "pin_reset"].groupby("customer_id")["t"].max().to_dict()
        self.today_received: dict[str, int] = {}
        self.version = f"ai1-lightgbm-{self.source}"

    # ------------------------------------------------------------------ features
    def features(self, sender: str, recipient: str, amount: float, hour: float = 19.0, channel: str = "app",
                 minutes_since_cash_in: float | None = None, device_changed_recently: bool | None = None,
                 pin_reset_recently: bool | None = None) -> tuple[dict, dict]:
        s, r, D = cidx(sender), cidx(recipient), self.D
        now_t = D * DAY + int(hour * 3600)
        c30, s30, q30 = self.c30[s], self.s30[s], self.q30[s]
        mean30 = s30 / c30 if c30 > 0 else float("nan")
        std30 = math.sqrt(max(q30 / c30 - mean30 ** 2, 0) + (0.1 * mean30 + 50) ** 2) if c30 > 0 else float("nan")
        gap = minutes_since_cash_in
        if gap is None:
            t_in = self.last_in.get(sender)
            gap = 1440.0 if t_in is None else min(1440.0, (now_t - t_in) / 60)
        dev = device_changed_recently if device_changed_recently is not None else (
            sender in self.last_dev and now_t - self.last_dev[sender] <= 72 * 3600)
        pin = pin_reset_recently if pin_reset_recently is not None else (
            sender in self.last_pin and now_t - self.last_pin[sender] <= 72 * 3600)
        f = {
            "sender_tenure_days": D - self.reg[s], "amount_log": math.log1p(amount),
            "amount_z_30d": (amount - mean30) / std30 if c30 >= 2 else float("nan"),
            "amount_to_balance": min(5.0, max(0.0, amount / (self.bal[s] + 1.0))),
            "sender_out_count_7d": self.out7[s], "cash_in_gap_min": float(gap),
            "device_change_72h": int(bool(dev)), "pin_reset_72h": int(bool(pin)),
            "first_time_pair": int((s, r) not in self.pairs),
            "recipient_age_days": D - self.reg[r], "recipient_in_count_7d": self.in7[r],
            "recipient_sender_days_7d": self.sdays7[r], "recipient_in_today_before": self.today_received.get(recipient, 0),
            "recipient_out_in_ratio_7d": min(5.0, max(0.0, self.outamt7[r] / (self.inamt7[r] + 100.0))),
            "recipient_cashout_count_7d": self.cash7[r], "hour": float(hour),
            "is_night": int(hour < 6 or hour >= 22), "dow": int((START + pd.Timedelta(days=D)).dayofweek),
            "channel_ussd": int(channel == "ussd"),
        }
        ctx = {"mean30": mean30, "std30": std30, "balance": float(self.bal[s])}
        return {k: float(v) if v == v else float("nan") for k, v in f.items()}, ctx

    def _raw(self, rows: list[dict]) -> np.ndarray:
        return self.booster.predict(pd.DataFrame(rows)[FEATURES])

    # ------------------------------------------------------------------ scoring
    def check(self, sender: str, recipient: str, amount: float, with_counterfactual: bool = True, **kw) -> dict:
        f, ctx = self.features(sender, recipient, amount, **kw)
        X = pd.DataFrame([f])[FEATURES]
        raw = float(self.booster.predict(X)[0])
        p = float(self.calib.predict([raw])[0])
        cstate = str(self.conf.state([p])[0])
        in0, in1 = self.conf.predict_set([p])
        ood = bool(self.nov.flag(X)[0])
        d = decide(raw, cstate, ood, self.thr, amount, self.rules)
        contrib = self.booster.predict(X, pred_contrib=True)[0]
        reasons = top_reasons(contrib, f, FEATURES)
        return {
            "model_version": self.version, "features": f, "model_score": raw, "calibrated_probability": p,
            "conformal_set": [lab for lab, on in (("normal", bool(in0[0])), ("scam", bool(in1[0]))) if on],
            "ood_flag": ood, **d, "reasons": reasons,
            "counterfactual": self.counterfactual(f, ctx, amount) if with_counterfactual else None,
            "thresholds": {"amber_p": self.thr.get("amber_p"), "red_p": self.thr.get("red_p")},
        }

    def counterfactual(self, f: dict, ctx: dict, amount: float) -> dict | None:
        """Largest lower amount that would bring the risk below the amber line (other facts unchanged)."""
        if amount <= 100:
            return None
        grid = np.unique(np.round(np.geomspace(100, amount, 24) / 50) * 50)[::-1]
        rows = []
        for a in grid:
            g = dict(f)
            g["amount_log"] = math.log1p(a)
            if ctx["std30"] == ctx["std30"] and f["amount_z_30d"] == f["amount_z_30d"]:
                g["amount_z_30d"] = (a - ctx["mean30"]) / ctx["std30"]
            g["amount_to_balance"] = min(5.0, a / (ctx["balance"] + 1.0))
            rows.append(g)
        raw = self._raw(rows)
        ok = np.where(raw <= self.thr["amber_score"])[0]
        if raw[-1] > self.thr["amber_score"]:
            return {"amount_bdt": None, "text_en": "Lowering the amount would not lower the risk much: the receiver is the main concern.",
                    "text_bn": "টাকার পরিমাণ কমালেও ঝুঁকি খুব একটা কমবে না: মূল সমস্যা প্রাপক।"}
        if not len(ok):
            return None
        a = float(grid[ok[0]])
        if a >= amount:
            return None
        return {"amount_bdt": a, "text_en": f"If the amount were Tk {a:,.0f} or less, the risk would drop below the warning level.",
                "text_bn": f"পরিমাণ {a:,.0f} টাকা বা কম হলে ঝুঁকি সতর্কতার সীমার নিচে নেমে আসত।"}

    def record_transfer(self, recipient: str) -> None:
        """Count transfers made during the demo 'today' (feeds recipient_in_today_before)."""
        self.today_received[recipient] = self.today_received.get(recipient, 0) + 1
