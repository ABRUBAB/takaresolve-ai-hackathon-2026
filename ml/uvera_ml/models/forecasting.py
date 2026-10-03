"""AI-3 Cash-Flow Guardian and AI-4 Agent Liquidity Copilot (both use uvera_ml.forecast).

Event probabilities ("balance below the floor at the end of the next 7 days", "cash demand above the agent's cash on
hand") are NOT obtained by adding daily quantiles (quantiles of a sum are not the sum of quantiles). Instead we use an
empirical, conformal-style method: on validation origins we record how real outcomes scattered around the forecast,
normalised by each series' own forecast width, and read probabilities from that empirical distribution. The warning
threshold is chosen on validation (best F1), never fixed at 0.5 and never tuned on the test set.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from uvera_ml import forecast as F
from uvera_ml.common import load_config, write_json
from uvera_ml.eval import metrics as M
from uvera_ml.eval import plots

PROBS = np.linspace(0, 1, 1001)


def _summarise(res: pd.DataFrame) -> list[dict]:
    return (res.groupby(["split", "model"])[["mase", "pinball_mean", "coverage_80", "mean_width_80"]].mean()
            .round(4).reset_index().to_dict("records"))


def ecdf(sorted_r: np.ndarray, z) -> np.ndarray:
    """P(R <= z) from a sorted sample."""
    return np.searchsorted(sorted_r, np.asarray(z, float), side="right") / max(1, len(sorted_r))


def residual_quantiles(r: np.ndarray) -> list[float]:
    return np.quantile(r, PROBS).tolist()


def cdf_from_quantiles(q: list[float], z) -> np.ndarray:
    """P(R <= z) using the exported quantile table (used by the API)."""
    q = np.asarray(q, float)
    return np.interp(np.asarray(z, float), q, PROBS, left=0.0, right=1.0)


def best_threshold(p: np.ndarray, y: np.ndarray, beta: float = 1.0, max_flag_rate: float = 1.0) -> float:
    """Validation-only operating point: best F-beta among cut-offs that warn on at most `max_flag_rate` of cases
    (an alert budget, like AI-1), so a weak signal can never 'win' by warning everyone."""
    best_t, best_f = float(np.quantile(p, 1 - max_flag_rate)), -1.0
    for t in np.unique(np.quantile(p, np.linspace(0.0, 0.995, 200))):
        flag = p >= t
        tp = float((flag & (y == 1)).sum())
        if tp == 0 or flag.mean() > max_flag_rate:
            continue
        prec, rec = tp / flag.sum(), tp / max(1, (y == 1).sum())
        f = (1 + beta ** 2) * prec * rec / (beta ** 2 * prec + rec)
        if f > best_f:
            best_t, best_f = float(t), f
    return best_t


def _prob_metrics(p: np.ndarray, y: np.ndarray, base: np.ndarray, thr: float | None) -> dict:
    def at(t):
        flag = p >= t
        return {"threshold": float(t), "recall": float(flag[y == 1].mean()) if y.any() else None,
                "precision": float(y[flag].mean()) if flag.any() else None, "flag_rate": float(flag.mean())}

    out = {"events": int(y.sum()), "n": int(len(y)), "base_rate": float(y.mean()), "brier": M.brier(y, p),
           "brier_baseline": M.brier(y, base), "pr_auc": M.pr_auc(y, p), "pr_auc_baseline": M.pr_auc(y, base),
           "ece": M.ece(y, p), "at_0.5_for_reference": at(0.5)}
    if thr is not None:
        out["at_validation_threshold"] = at(thr)
    return out


def _cross_fit(val: pd.DataFrame, z_col: str, upper_tail: bool) -> np.ndarray:
    """Probabilities for validation rows using residuals from the OTHER validation origins (no in-sample optimism)."""
    out = np.zeros(len(val))
    origins = val["origin"].unique()
    for o in origins:
        mask = (val["origin"] == o).to_numpy()
        pool = val.loc[~mask, "r"] if len(origins) > 1 else val["r"]
        c = ecdf(np.sort(pool.to_numpy()), val.loc[mask, z_col])
        out[mask] = 1 - c if upper_tail else c
    return out


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

    # event: balance below the floor at the END of the next 7 days
    actual = s.set_index(["id", "day"])["target"]
    p = p.assign(actual=actual.reindex(pd.MultiIndex.from_arrays([p["id"], p["day"]])).to_numpy())
    agg = p.groupby(["id", "origin", "split"]).agg(mu=("q0.5", "sum"), lo=("q0.1", "sum"), hi=("q0.9", "sum"),
                                                   actual_sum=("actual", "sum")).reset_index()
    bal0 = s.set_index(["id", "day"])["balance_sod"]
    end = s.set_index(["id", "day"])["balance_eod"]
    agg["balance_now"] = bal0.reindex(pd.MultiIndex.from_arrays([agg["id"], agg["origin"]])).to_numpy()
    agg["balance_end_actual"] = end.reindex(pd.MultiIndex.from_arrays([agg["id"], agg["origin"] + F.HORIZON - 1])).to_numpy()
    agg = agg.dropna(subset=["balance_now", "balance_end_actual"])
    agg["actual_shortfall"] = (agg["balance_end_actual"] < floor).astype(int)
    agg["scale"] = np.maximum(agg["hi"] - agg["lo"], 1.0)
    agg["r"] = (agg["actual_sum"] - agg["mu"]) / agg["scale"]
    agg["z"] = (floor - agg["balance_now"] - agg["mu"]) / agg["scale"]
    agg["p_naive"] = 1 - F.normal_prob_above(floor - agg["balance_now"], agg["lo"], agg["mu"], agg["hi"])

    val, te = agg[agg["split"] == "val"].copy(), agg[agg["split"] == "test"].copy()
    val["p_shortfall"] = _cross_fit(val, "z", upper_tail=False)
    budget = load_config("thresholds").get("ai3_cashflow", {}).get("max_warning_rate", 0.30)
    thr = best_threshold(val["p_shortfall"].to_numpy(), val["actual_shortfall"].to_numpy(), beta=1.0, max_flag_rate=budget)
    R = np.sort(val["r"].to_numpy())
    te["p_shortfall"] = ecdf(R, te["z"])
    lo_r, hi_r = np.quantile(R, [0.1, 0.9])
    interval_cov = float(((te["actual_sum"] >= te["mu"] + lo_r * te["scale"]) & (te["actual_sum"] <= te["mu"] + hi_r * te["scale"])).mean())

    y = te["actual_shortfall"].to_numpy()
    hist = s[s["day"] < F.origins(world.n_days)["train_end"]].groupby("id")["balance_eod"].apply(lambda b: (b < floor).mean())
    base = te["id"].map(hist).fillna(0).to_numpy()

    ex = s["id"].iloc[0]
    o0 = p["origin"].min()
    hist_days = s[(s["id"] == ex) & (s["day"] >= o0 - 21) & (s["day"] < o0 + F.HORIZON)]
    pe = p[(p["id"] == ex) & (p["origin"] == o0)].merge(hist_days[["day", "date"]], on="day")
    if len(pe):
        plots.forecast_band(pe["date"], hist_days.set_index("day").loc[pe["day"], "target"], pe["q0.1"], pe["q0.5"], pe["q0.9"],
                            rep / "figures" / "ai3_forecast_example.png", f"AI-3 net cash-flow forecast ({winner})")
    plots.reliability({"empirical (ours)": M.reliability_table(y, te["p_shortfall"]),
                       "sum-of-quantiles normal (naive)": M.reliability_table(y, te["p_naive"])},
                      rep / "figures" / "ai3_shortfall_reliability.png", "AI-3 shortfall probability calibration (test)")

    p[p["split"] == "test"].drop(columns=["actual"]).to_parquet(art / "forecasts.parquet", index=False)
    te.drop(columns=["r", "actual_sum"]).to_parquet(art / "shortfall.parquet", index=False)
    write_json(art / "residuals.json", {"method": "empirical normalised 7-day-sum residuals (validation origins)",
                                        "quantiles": residual_quantiles(R), "threshold": thr, "floor_bdt": floor,
                                        "horizon_days": F.HORIZON})
    summary = {"ai": "AI-3 Cash-Flow Guardian", "target": "daily net flow (inflow - outflow)", "horizon_days": F.HORIZON,
               "event": f"balance below Tk {floor} at the end of the next {F.HORIZON} days",
               "n_series": int(s["id"].nunique()), "winner_on_validation": winner, "backtest": _summarise(res),
               "probability_method": "empirical normalised residuals of the 7-day sum (calibrated on validation origins)",
               "validation_threshold": thr, "threshold_rule": "best F1 on validation within an alert budget (configs/thresholds.yaml)",
               "seven_day_sum_80pct_interval_coverage_test": interval_cov,
               "shortfall_probability_test": _prob_metrics(te["p_shortfall"].to_numpy(), y, base, thr),
               "shortfall_probability_test_naive_sum_of_quantiles": _prob_metrics(te["p_naive"].to_numpy(), y, base, thr),
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
    act = s.set_index(["id", "day"])["target"]
    p["actual"] = act.reindex(pd.MultiIndex.from_arrays([p["id"], p["day"]])).to_numpy()
    p["actual_stockout"] = (p["actual"] > p["capacity"]).astype(int)
    p["scale"] = np.maximum(p["q0.9"] - p["q0.1"], 1.0)
    p["r"] = (p["actual"] - p["q0.5"]) / p["scale"]
    p["z"] = (p["capacity"] - p["q0.5"]) / p["scale"]
    p["p_naive"] = F.normal_prob_above(p["capacity"], p["q0.1"], p["q0.5"], p["q0.9"])
    p["topup_needed_bdt"] = np.maximum(0, np.round((p["q0.9"] - p["capacity"]) / 500) * 500)

    val, te = p[p["split"] == "val"].copy(), p[p["split"] == "test"].copy()
    R = np.sort(val["r"].to_numpy())
    te["p_stockout"] = 1 - ecdf(R, te["z"])
    y = te["actual_stockout"].to_numpy()
    tr = s[s["day"] < org["train_end"]].assign(dow=lambda d: d["date"].dt.dayofweek, cap=lambda d: d["id"].map(cap))
    freq = (tr["target"] > tr["cap"]).groupby([tr["id"], tr["dow"]]).mean()
    dows = (pd.Timestamp(world.meta["start"]) + pd.to_timedelta(te["day"], unit="D")).dt.dayofweek
    base = freq.reindex(pd.MultiIndex.from_arrays([te["id"], dows])).fillna(0).to_numpy()
    te["p_history"] = base

    # What the product does (API + agent page): recommend cash to hold for a 90%-safe day. No probability cut-off is
    # used: stock-out rates differ a lot between weeks (validation 39% vs test 21% of agent-days here), so a cut-off
    # frozen on validation does not transfer. Two diagnostics below show where the stock-out probability has skill.
    def two_riskiest(col: str) -> np.ndarray:  # within one agent's week: which days run short?
        r = te.groupby(["id", "origin"])[col].rank(method="first", ascending=False)
        return (r <= 2).to_numpy()

    def top_share(col: str, share: float = 0.2) -> np.ndarray:  # across all agents in a week: who runs short?
        r = te.groupby("origin")[col].rank(method="first", ascending=False, pct=True)
        return (r <= share).to_numpy()

    def hit_rate(flag: np.ndarray) -> dict:
        return {"recall": float(flag[y == 1].mean()) if y.any() else None, "precision": float(y[flag].mean()) if flag.any() else None,
                "flag_rate": float(flag.mean())}

    day_ranking = {"question": "within one agent-week, are the two highest-probability days the ones that run short?",
                   "model": hit_rate(two_riskiest("p_stockout")), "history_baseline": hit_rate(two_riskiest("p_history")),
                   "chance_precision": float(y.mean()),
                   "finding": "no better than chance, so the product does not flag days"}
    agent_ranking = {"question": "across all agents each week, do the top 20% agent-days by probability run short more often?",
                     "model": hit_rate(top_share("p_stockout")), "history_baseline": hit_rate(top_share("p_history")),
                     "chance_precision": float(y.mean())}

    def hold(cash: np.ndarray) -> dict:
        cash = np.asarray(cash, float)
        return {"days_short_of_cash": float((te["actual"].to_numpy() > cash).mean()), "mean_cash_bdt": float(cash.mean()),
                "extra_vs_usual_bdt": float((cash - te["capacity"].to_numpy()).mean())}

    q90 = te["q0.9"].to_numpy()
    cash_to_hold = {"target_days_short": 0.10, "usual_cash": hold(te["capacity"]), "forecast_q90": hold(q90),
                    "same_extra_cash_spread_flat": hold(te["capacity"].to_numpy() * q90.mean() / te["capacity"].mean())}
    if "seasonal_naive" in preds and winner != "seasonal_naive":
        sn = preds["seasonal_naive"]
        sn = te[["id", "day", "origin"]].merge(sn[sn["split"] == "test"][["id", "day", "origin", "q0.9"]], on=["id", "day", "origin"], how="left")
        cash_to_hold["seasonal_naive_q90"] = hold(sn["q0.9"].fillna(te["capacity"].mean()).to_numpy())

    ex = s["id"].iloc[0]
    o0 = te["origin"].min()
    hist_days = s[(s["id"] == ex) & (s["day"] >= o0 - 21) & (s["day"] < o0 + F.HORIZON)]
    pe = te[(te["id"] == ex) & (te["origin"] == o0)].merge(hist_days[["day", "date"]], on="day")
    if len(pe):
        plots.forecast_band(pe["date"], pe["actual"], pe["q0.1"], pe["q0.5"], pe["q0.9"],
                            rep / "figures" / "ai4_forecast_example.png", f"AI-4 agent cash-out demand ({winner})")
    plots.reliability({"empirical (ours)": M.reliability_table(y, te["p_stockout"]),
                       "normal approximation (naive)": M.reliability_table(y, te["p_naive"])},
                      rep / "figures" / "ai4_stockout_reliability.png", "AI-4 stock-out probability calibration (test)")

    te.drop(columns=["r"]).to_parquet(art / "forecasts.parquet", index=False)
    write_json(art / "residuals.json", {"method": "empirical normalised daily residuals (validation origins)",
                                        "quantiles": residual_quantiles(R), "threshold": None})
    pd.DataFrame({"agent_id": cap.index, "capacity_bdt": cap.round(0).to_numpy()}).to_parquet(art / "capacity.parquet", index=False)
    summary = {"ai": "AI-4 Agent Liquidity Copilot", "target": "daily cash-out demand per agent", "horizon_days": F.HORIZON,
               "event": "cash-out demand above the agent's cash on hand on that day",
               "n_agents": int(s["id"].nunique()), "winner_on_validation": winner, "backtest": _summarise(res),
               "capacity_rule": "agent_capacity_factor x mean daily demand in the training window [ASSUMPTION]",
               "probability_method": "empirical normalised residuals (calibrated on validation origins)",
               "operating_rule": "hold the 90% forecast (cash to hold); no day-level yes/no alarm", "stockout_base_rate": {"validation": float(val["actual_stockout"].mean()),
                                                                           "test": float(y.mean())},
               "cash_to_hold_test": cash_to_hold, "day_ranking_test": day_ranking, "agent_ranking_test": agent_ranking,
               "stockout_probability_test": _prob_metrics(te["p_stockout"].to_numpy(), y, base, None),
               "stockout_probability_test_naive_normal": _prob_metrics(te["p_naive"].to_numpy(), y, base, None),
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
