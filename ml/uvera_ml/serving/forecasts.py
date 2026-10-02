"""AI-3 / AI-4 live forecasts for the next 7 days (LightGBM-quantile fitted at startup on the full history)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from uvera_ml import forecast as F
from uvera_ml.common import load_config
from uvera_ml.models.forecasting import savings_options
from uvera_ml.serving.store import ArtifactStore
from uvera_ml.sim.world import START, World
from uvera_ml.uncertainty.calibration import IsotonicCalibrator


def _future(ids, D, n, festival):
    rows = [{"id": i, "day": d, "date": START + pd.Timedelta(days=d)} for i in ids for d in range(D, D + n)]
    return F.add_calendar(pd.DataFrame(rows), festival)


def _cal(store, rel):
    j = store.json(rel)
    return IsotonicCalibrator.from_json(j) if j else None


class ForecastEngine:
    def __init__(self, world: World, store: ArtifactStore, n_fit_customers: int = 3000):
        self.w, self.D, self.fest = world, world.n_days, world.meta["festival_days"]
        self.floor = load_config("assumptions").get("shortfall_floor_bdt", 200)
        dc = world.daily_customer.rename(columns={"customer_id": "id"}).copy()
        dc["target"] = dc["inflow"] - dc["outflow"]
        self.cust = F.add_calendar(dc[["id", "day", "date", "target", "inflow", "outflow", "balance_sod", "balance_eod"]], self.fest)
        sample = F.customer_series(world, n_fit_customers)
        self.cust_model = F.LGBQuantile().fit(sample)
        self.agents = F.agent_series(world)
        self.agent_model = F.LGBQuantile().fit(self.agents)
        cap = store.parquet("artifacts/ai4/capacity.parquet")
        self.capacity = (cap.set_index("agent_id")["capacity_bdt"] if cap is not None
                         else F.capacity(self.agents, F.origins(self.D)["train_end"]))
        self.short_cal = _cal(store, "artifacts/ai3/shortfall_calibrator.json")
        self.stock_cal = _cal(store, "artifacts/ai4/stockout_calibrator.json")
        m3, m4 = store.json("reports/metrics_ai3.json", {}) or {}, store.json("reports/metrics_ai4.json", {}) or {}
        self.winner = {"ai3": m3.get("winner_on_validation", "not measured yet"), "ai4": m4.get("winner_on_validation", "not measured yet")}
        self.source = {"ai3": store.source_of("ai3"), "ai4": store.source_of("ai4")}

    # ------------------------------------------------------------------ customers (AI-3)
    def customer(self, cid: str, goal_bdt: float | None = None, months: int | None = None) -> dict:
        hist = self.cust[self.cust["id"] == cid].sort_values("day")
        if hist.empty:
            raise KeyError(cid)
        fut = _future([cid], self.D, 7, self.fest)
        pred = self.cust_model.predict(hist, fut).sort_values("day").rename(columns={"q0.1": "q10", "q0.5": "q50", "q0.9": "q90"})
        bal_now = float(hist["balance_eod"].iloc[-1])
        mu, lo, hi = pred["q50"].sum(), pred["q10"].sum(), pred["q90"].sum()
        p_raw = float(1 - F.normal_prob_above(self.floor - bal_now, lo, mu, hi))
        p = float(self.short_cal.predict([p_raw])[0]) if self.short_cal else p_raw
        last = hist.tail(56).copy()
        last["week"] = (last["day"] // 7).astype(int)
        weeks = last.groupby("week").agg(outflow=("outflow", "sum"), start_day=("day", "min")).reset_index()
        heavy = weeks.sort_values("outflow", ascending=False).head(2)
        net = hist.tail(60)["target"].to_numpy()
        rng = np.random.default_rng(7)
        monthly = np.array([rng.choice(net, 30).sum() for _ in range(400)]) if len(net) >= 10 else np.zeros(1)
        q10, q50 = float(max(0, np.quantile(monthly, 0.1))), float(max(0, np.quantile(monthly, 0.5)))
        plans = savings_options(goal_bdt, months, q10, q50) if goal_bdt and months else []
        return {
            "customer_id": cid, "model": "lightgbm-quantile (live)", "validated_winner": self.winner["ai3"],
            "source": self.source["ai3"], "balance_now_bdt": bal_now, "floor_bdt": self.floor,
            "history": [{"date": str(r.date.date()), "net": float(r.target), "inflow": float(r.inflow), "outflow": float(r.outflow),
                         "balance": float(r.balance_eod)} for r in hist.tail(35).itertuples()],
            "forecast": [{"date": str((START + pd.Timedelta(days=int(r.day))).date()), "q10": float(r.q10), "q50": float(r.q50),
                          "q90": float(r.q90)} for r in pred.itertuples()],
            "p_shortfall_7d": p, "p_shortfall_uncalibrated": p_raw,
            "heavy_outflow_weeks": [{"week_start": str((START + pd.Timedelta(days=int(r.start_day))).date()),
                                     "outflow_bdt": float(r.outflow)} for r in heavy.itertuples()],
            "monthly_free_cash": {"q10": q10, "q50": q50}, "savings_plans": plans,
        }

    # ------------------------------------------------------------------ agents (AI-4)
    def agent(self, aid: str) -> dict:
        hist = self.agents[self.agents["id"] == aid].sort_values("day")
        if hist.empty:
            raise KeyError(aid)
        fut = _future([aid], self.D, 7, self.fest)
        pred = self.agent_model.predict(hist, fut).sort_values("day").rename(columns={"q0.1": "q10", "q0.5": "q50", "q0.9": "q90"})
        cap = float(self.capacity.get(aid, hist["target"].mean() * 1.5))
        p_raw = F.normal_prob_above(cap, pred["q10"], pred["q50"], pred["q90"])
        p = self.stock_cal.predict(p_raw) if self.stock_cal else p_raw
        days = []
        for r, pr_, praw in zip(pred.itertuples(), p, p_raw):
            date = START + pd.Timedelta(days=int(r.day))
            need = max(0.0, round((r.q90 - cap) / 500) * 500)
            days.append({"date": str(date.date()), "weekday": date.day_name(), "q10": float(r.q10), "q50": float(r.q50),
                         "q90": float(r.q90), "p_stockout": float(pr_), "p_stockout_uncalibrated": float(praw),
                         "topup_bdt": need if pr_ >= 0.3 else 0.0})
        ag = self.w.agents.set_index("agent_id").loc[aid]
        peers = self.w.agents[(self.w.agents["zone"] == ag["zone"]) & (self.w.agents["size"] == ag["size"])]["agent_id"]
        recent = self.agents[self.agents["day"] >= self.D - 28]
        peer_daily = recent[recent["id"].isin(peers)].groupby("id")["target"].mean()
        mine_recent = float(hist[hist["day"] >= self.D - 28]["target"].mean())
        mine_before = float(hist[(hist["day"] >= self.D - 56) & (hist["day"] < self.D - 28)]["target"].mean())
        return {
            "agent_id": aid, "zone": ag["zone"], "size": ag["size"], "model": "lightgbm-quantile (live)",
            "validated_winner": self.winner["ai4"], "source": self.source["ai4"], "capacity_bdt": cap,
            "history": [{"date": str(r.date.date()), "cash_out": float(r.target), "cash_in": float(r.cash_in)} for r in hist.tail(35).itertuples()],
            "forecast": days,
            "peers": {"n": int(len(peer_daily)), "median_daily_cash_out": float(peer_daily.median()),
                      "p25": float(peer_daily.quantile(0.25)), "p75": float(peer_daily.quantile(0.75)),
                      "mine_last_28d": mine_recent, "mine_previous_28d": mine_before,
                      "change_pct": float((mine_recent - mine_before) / max(mine_before, 1) * 100)},
        }
