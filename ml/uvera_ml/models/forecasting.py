"""AI-3 Cash-Flow Guardian and AI-4 Agent Liquidity Copilot (both use uvera_ml.forecast)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from uvera_ml import forecast as F
from uvera_ml.common import load_config, write_json
from uvera_ml.eval import metrics as M
from uvera_ml.eval import plots
from uvera_ml.uncertainty.calibration import IsotonicCalibrator


def _summarise(res: pd.DataFrame) -> list[dict]:
    return (res.groupby(["split", "model"])[["mase", "pinball_mean", "coverage_80", "mean_width_80"]].mean()
            .round(4).reset_index().to_dict("records"))


def _prob_metrics(p: np.ndarray, y: np.ndarray, base: np.ndarray) -> dict:
    flag = p >= 0.5
    return {"events": int(y.sum()), "n": int(len(y)), "brier": M.brier(y, p), "brier_baseline": M.brier(y, base),
            "pr_auc": M.pr_auc(y, p), "pr_auc_baseline": M.pr_auc(y, base), "ece": M.ece(y, p),
            "recall_at_0.5": float(flag[y == 1].mean()) if y.any() else None,
            "precision_at_0.5": float(y[flag].mean()) if flag.any() else None}


def run_ai3(world, out: str | Path, n_customers: int = 2000, use_chronos: bool = True) -> dict:
    out = Path(out)
    art, rep = out / "artifacts" / "ai3", out / "reports"
    art.mkdir(parents=True, exist_ok=True)
    (rep / "figures").mkdir(parents=True, exist_ok=True)
    floor = load_config("assumptions").get("shortfall_floor_bdt", 200)

    s = F.customer_series(world, n_customers)
    res, preds = F.backtest(s, world.n_days, use_chronos)
    winner = F.pick_winner(res)
    p = preds[winner]

    # P(shortfall): balance at the end of the 7-day horizon falls below the floor
    agg = p.groupby(["id", "origin"]).agg(mu=("q0.5", "sum"), lo=("q0.1", "sum"), hi=("q0.9", "sum")).reset_index()
    bal0 = s.set_index(["id", "day"])["balance_sod"]
    agg["balance_now"] = bal0.reindex(pd.MultiIndex.from_arrays([agg["id"], agg["origin"]])).to_numpy()
    agg["p_shortfall"] = 1 - F.normal_prob_above(floor - agg["balance_now"], agg["lo"], agg["mu"], agg["hi"])
    end = s.set_index(["id", "day"])["balance_eod"]
    agg["balance_end_actual"] = end.reindex(pd.MultiIndex.from_arrays([agg["id"], agg["origin"] + F.HORIZON - 1])).to_numpy()
    agg = agg.dropna(subset=["balance_now", "balance_end_actual"])
    agg["actual_shortfall"] = (agg["balance_end_actual"] < floor).astype(int)
    agg["split"] = agg["origin"].map(p.drop_duplicates("origin").set_index("origin")["split"])
    val, te = agg[agg["split"] == "val"], agg[agg["split"] == "test"].copy()
    calib = IsotonicCalibrator().fit(val["p_shortfall"], val["actual_shortfall"])  # recalibrated on validation origins
    te["p_shortfall_raw"] = te["p_shortfall"]
    te["p_shortfall"] = calib.predict(te["p_shortfall_raw"])
    y = te["actual_shortfall"].to_numpy()
    hist = s[s["day"] < F.origins(world.n_days)["train_end"]].groupby("id")["balance_eod"].apply(lambda b: (b < floor).mean())
    base = te["id"].map(hist).fillna(0).to_numpy()
    raw_metrics = _prob_metrics(te["p_shortfall_raw"].to_numpy(), y, base)
    agg = te

    ex = s["id"].iloc[0]
    o0 = p["origin"].min()
    hist_days = s[(s["id"] == ex) & (s["day"] >= o0 - 21) & (s["day"] < o0 + F.HORIZON)]
    pe = p[(p["id"] == ex) & (p["origin"] == o0)].merge(hist_days[["day", "date"]], on="day")
    if len(pe):
        plots.forecast_band(pe["date"], hist_days.set_index("day").loc[pe["day"], "target"], pe["q0.1"], pe["q0.5"], pe["q0.9"],
                            rep / "figures" / "ai3_forecast_example.png", f"AI-3 net cash-flow forecast ({winner})")

    p = p[p["split"] == "test"]
    p.to_parquet(art / "forecasts.parquet", index=False)
    agg.to_parquet(art / "shortfall.parquet", index=False)
    write_json(art / "shortfall_calibrator.json", calib.to_json())
    summary = {"ai": "AI-3 Cash-Flow Guardian", "target": "daily net flow (inflow - outflow)", "horizon_days": F.HORIZON,
               "n_series": int(s["id"].nunique()), "winner_on_validation": winner, "backtest": _summarise(res),
               "shortfall_floor_bdt": floor, "shortfall_probability_test": _prob_metrics(agg["p_shortfall"].to_numpy(), y, base),
               "shortfall_probability_test_before_recalibration": raw_metrics,
               "baseline": "historical frequency of low balance (training window)"}
    write_json(rep / "metrics_ai3.json", summary)
    res.to_csv(rep / "ai3_backtest.csv", index=False)
    return summary


def run_ai4(world, out: str | Path, use_chronos: bool = True) -> dict:
    out = Path(out)
    art, rep = out / "artifacts" / "ai4", out / "reports"
    art.mkdir(parents=True, exist_ok=True)
    (rep / "figures").mkdir(parents=True, exist_ok=True)

    s = F.agent_series(world)
    org = F.origins(world.n_days)
    cap = F.capacity(s, org["train_end"])
    res, preds = F.backtest(s, world.n_days, use_chronos)
    winner = F.pick_winner(res)
    p = preds[winner].copy()
    p["capacity"] = p["id"].map(cap)
    p["p_stockout"] = F.normal_prob_above(p["capacity"], p["q0.1"], p["q0.5"], p["q0.9"])
    p["topup_needed_bdt"] = np.maximum(0, np.round((p["q0.9"] - p["capacity"]) / 500) * 500)
    act = s.set_index(["id", "day"])["target"]
    p["actual"] = act.reindex(pd.MultiIndex.from_arrays([p["id"], p["day"]])).to_numpy()
    p["actual_stockout"] = (p["actual"] > p["capacity"]).astype(int)
    vp = p[p["split"] == "val"]
    calib = IsotonicCalibrator().fit(vp["p_stockout"], vp["actual_stockout"])
    p = p[p["split"] == "test"].copy()
    p["p_stockout_raw"] = p["p_stockout"]
    p["p_stockout"] = calib.predict(p["p_stockout_raw"])
    y = p["actual_stockout"].to_numpy()
    tr = s[s["day"] < org["train_end"]].assign(dow=lambda d: d["date"].dt.dayofweek, cap=lambda d: d["id"].map(cap))
    freq = (tr["target"] > tr["cap"]).groupby([tr["id"], tr["dow"]]).mean()
    dows = (pd.Timestamp(world.meta["start"]) + pd.to_timedelta(p["day"], unit="D")).dt.dayofweek
    base = freq.reindex(pd.MultiIndex.from_arrays([p["id"], dows])).fillna(0).to_numpy()

    ex = s["id"].iloc[0]
    o0 = p["origin"].min()
    hist_days = s[(s["id"] == ex) & (s["day"] >= o0 - 21) & (s["day"] < o0 + F.HORIZON)]
    pe = p[(p["id"] == ex) & (p["origin"] == o0)].merge(hist_days[["day", "date"]], on="day")
    if len(pe):
        plots.forecast_band(pe["date"], pe["actual"], pe["q0.1"], pe["q0.5"], pe["q0.9"],
                            rep / "figures" / "ai4_forecast_example.png", f"AI-4 agent cash-out demand ({winner})")

    p.to_parquet(art / "forecasts.parquet", index=False)
    write_json(art / "stockout_calibrator.json", calib.to_json())
    pd.DataFrame({"agent_id": cap.index, "capacity_bdt": cap.round(0).to_numpy()}).to_parquet(art / "capacity.parquet", index=False)
    summary = {"ai": "AI-4 Agent Liquidity Copilot", "target": "daily cash-out demand per agent", "horizon_days": F.HORIZON,
               "n_agents": int(s["id"].nunique()), "winner_on_validation": winner, "backtest": _summarise(res),
               "capacity_rule": "agent_capacity_factor x mean daily demand in the training window [ASSUMPTION]",
               "stockout_probability_test": _prob_metrics(p["p_stockout"].to_numpy(), y, base),
               "stockout_probability_test_before_recalibration": _prob_metrics(p["p_stockout_raw"].to_numpy(), y, base),
               "baseline": "historical stock-out frequency per agent and weekday (training window)"}
    write_json(rep / "metrics_ai4.json", summary)
    res.to_csv(rep / "ai4_backtest.csv", index=False)
    return summary


def savings_options(goal_bdt: float, months: int, monthly_free_cash_q10: float, monthly_free_cash_q50: float) -> list[dict]:
    """Three savings plans. 'Safe' uses the 10% quantile of free cash so it survives bad weeks (never automatic)."""
    need = goal_bdt / max(1, months)
    plans = [("safe", monthly_free_cash_q10 * 0.8), ("balanced", (monthly_free_cash_q10 + monthly_free_cash_q50) / 2),
             ("ambitious", monthly_free_cash_q50 * 0.9)]
    out = []
    for name, per_month in plans:
        per_month = max(0.0, round(per_month / 50) * 50)
        out.append({"plan": name, "monthly_bdt": per_month,
                    "months_to_goal": None if per_month <= 0 else int(np.ceil(goal_bdt / per_month)),
                    "meets_deadline": per_month >= need})
    return out
