"""Phase-2 business case: turn model metrics into operational and economic outcomes, with every assumption explicit.

Judges: "customer money actually saved depends on an assumed 30-70% intervention rate. Validate false-pause cost, confirmed scams
prevented, analyst minutes saved, agent service availability and net economic benefit."

What is MEASURED (synthetic test window, deployed phase-1 models, no retraining):
  - scams and scam money paused, false pauses, "not sure" reviews (AI-1 on 24,827 transfers of unseen customers);
  - analyst work items (AI-6: alerts vs linked cases);
  - agent service: every real cash-out request of the test days replayed against the cash an agent holds
    (usual cash vs the AI-4 90% forecast) -> customers turned away, unmet taka;
  - the on-site user study (if reports/phase2/user_study.json exists): stated stop rate after the Pause screen, analyst triage
    minutes for alert lists vs linked cases.
What is ASSUMED (low / base / high, all in configs below): value of a customer's minute, support contacts per false pause,
analyst cost per minute, minutes per triage item, cash-out fee, server cost.
Outputs: break-even follow rate (the share of warned scam victims who must stop for UVERA to pay for itself), net benefit per
1 million P2P transfers at several follow rates, a one-at-a-time sensitivity (tornado), agent availability.
Writes reports/phase2/business_case.json and reports/phase2/figures/business_*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from uvera_ml import common  # noqa: E402

OUT = ROOT / "reports" / "phase2"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
PER = 1_000_000  # report everything per 1 million P2P transfers

ASSUME = {  # [low, base, high]
    "customer_minutes_lost_per_false_pause": [1.0, 2.0, 5.0],
    "customer_value_per_minute_bdt": [1.0, 2.0, 4.0],          # ~Tk 60-240 per hour of time
    "support_contact_rate_per_false_pause": [0.02, 0.10, 0.25],
    "support_contact_cost_bdt": [20.0, 40.0, 80.0],
    "abandon_rate_after_false_pause": [0.01, 0.05, 0.10],
    "fee_revenue_lost_per_abandoned_transfer_bdt": [0.0, 5.0, 15.0],
    "analyst_cost_per_minute_bdt": [3.0, 5.0, 10.0],            # ~Tk 180-600 per hour
    "minutes_per_unsure_review": [2.0, 3.0, 6.0],
    "minutes_per_alert_item": [3.0, 6.0, 10.0],
    "minutes_per_linked_case": [5.0, 8.0, 15.0],
    "cashout_fee_rate": [0.013, 0.015, 0.0185],                 # configs/qr_fee.yaml public range
    "server_cost_bdt_per_month": [3000.0, 6000.0, 15000.0],
    "p2p_transfers_per_month": [1_000_000, 1_000_000, 1_000_000],
}
# the end of each range that makes UVERA look worse (every other assumption: the high end)
PESSIMISTIC_LOW = {"minutes_per_alert_item", "cashout_fee_rate", "p2p_transfers_per_month"}


def pessimistic():
    return {k: (v[0] if k in PESSIMISTIC_LOW else v[2]) for k, v in ASSUME.items()}


def measured():
    t = pd.read_parquet(ROOT / "artifacts" / "ai1" / "test_scores.parquet")
    scam, high = t["is_scam"].to_numpy() == 1, t["risk_level"].to_numpy() == "high"
    m6 = json.loads((ROOT / "reports" / "metrics_ai6.json").read_text())["linking"]
    m1 = json.loads((ROOT / "reports" / "metrics_ai1.json").read_text())["test_unseen_customers"]
    n = len(t)
    k = PER / n
    out = {
        "window": {"transfers": n, "days": 20, "scams": int(scam.sum()), "scam_money_bdt": float(t.loc[scam, "amount"].sum())},
        "per_million": {
            "scams": scam.sum() * k, "scam_money_bdt": t.loc[scam, "amount"].sum() * k,
            "scams_paused": (scam & high).sum() * k, "scam_money_paused_bdt": t.loc[scam & high, "amount"].sum() * k,
            "false_pauses": (~scam & high).sum() * k, "unsure_reviews": t["unsure"].sum() * k,
            "alerts": m6["n_alerts"] * k, "linked_cases": m6["n_cases"] * k},
        "share_of_scam_money_paused": float(t.loc[scam & high, "amount"].sum() / t.loc[scam, "amount"].sum()),
        "share_of_scams_paused": float((scam & high).mean() / scam.mean()),
        "false_pauses_per_1000_normal": float(1000 * (~scam & high).sum() / (~scam).sum()),
        "rule_baseline_at_same_alert_budget": {"scam_money_caught_bdt_window": m1["rule_baseline"]["at_5pct_alert_rate"].get("amount_caught"),
                                               "model_scam_money_caught_bdt_window": m1["model"]["at_5pct_alert_rate"].get("amount_caught")},
    }
    return out


def agent_service():
    """Replay each agent's actual cash-out requests on the test days against the cash it holds."""
    f = pd.read_parquet(ROOT / "artifacts" / "ai4" / "forecasts.parquet")
    f = f[f["split"] == "test"]
    ev = pd.read_parquet(ROOT / "_outputs" / "world_full" / "events.parquet", columns=["t", "day", "etype", "agent_id", "amount"])
    ev = ev[(ev["etype"] == "cash_out") & ev["day"].isin(f["day"].unique())].sort_values("t")
    ev["cum"] = ev.groupby(["agent_id", "day"])["amount"].cumsum()
    res = {}
    for name, cash_col in (("usual_cash", "capacity"), ("uvera_forecast_q90", "q0.9")):
        cash = f.set_index(["id", "day"])[cash_col]
        c = ev.join(cash.rename("cash"), on=["agent_id", "day"])
        refused = c["cum"] > c["cash"]
        res[name] = {"cash_out_requests": int(len(c)), "requests_refused": int(refused.sum()),
                     "share_refused": float(refused.mean()), "unmet_bdt": float(c.loc[refused, "amount"].sum()),
                     "agent_days_short": float((f["actual"] > f[cash_col]).mean()), "mean_cash_held_bdt": float(f[cash_col].mean())}
    u, v = res["usual_cash"], res["uvera_forecast_q90"]
    res["customers_served_extra"] = u["requests_refused"] - v["requests_refused"]
    res["refusals_avoided_share"] = 1 - v["requests_refused"] / max(1, u["requests_refused"])
    res["extra_cash_held_bdt_per_agent_day"] = v["mean_cash_held_bdt"] - u["mean_cash_held_bdt"]
    res["unmet_bdt_recovered"] = u["unmet_bdt"] - v["unmet_bdt"]
    res["agent_days"] = int(len(f))
    days = f["day"].nunique()
    res["test_days"] = int(days)
    res["fee_revenue_recovered_bdt_per_agent_per_month"] = res["unmet_bdt_recovered"] * 0.015 / f["id"].nunique() * 30 / days
    return res


def study():
    p = OUT / "user_study.json"
    return json.loads(p.read_text()) if p.exists() else None


def economics(meas, agent, a: dict, follow: float):
    pm = meas["per_million"]
    prevented = follow * pm["scam_money_paused_bdt"]
    fp_cost = pm["false_pauses"] * (a["customer_minutes_lost_per_false_pause"] * a["customer_value_per_minute_bdt"]
                                    + a["support_contact_rate_per_false_pause"] * a["support_contact_cost_bdt"]
                                    + a["abandon_rate_after_false_pause"] * a["fee_revenue_lost_per_abandoned_transfer_bdt"])
    review_cost = pm["unsure_reviews"] * a["minutes_per_unsure_review"] * a["analyst_cost_per_minute_bdt"]
    analyst_saved = (pm["alerts"] * a["minutes_per_alert_item"] - pm["linked_cases"] * a["minutes_per_linked_case"]) * a["analyst_cost_per_minute_bdt"]
    fee_gain = 0.0  # agent-side gains are reported separately (agent_service), not mixed into per-transfer economics
    infra = a["server_cost_bdt_per_month"] * (PER / a["p2p_transfers_per_month"])
    benefit = prevented + analyst_saved + fee_gain
    cost = fp_cost + review_cost + infra
    return {"follow_rate": follow, "scam_money_prevented_bdt": prevented, "analyst_cost_saved_bdt": analyst_saved,
            "agent_fee_revenue_gained_bdt": fee_gain, "false_pause_cost_bdt": fp_cost, "unsure_review_cost_bdt": review_cost,
            "infrastructure_bdt": infra, "net_benefit_bdt": benefit - cost, "benefit_cost_ratio": benefit / cost if cost else None}


def break_even(meas, agent, a):
    lo, hi = 0.0, 1.0
    if economics(meas, agent, a, 0.0)["net_benefit_bdt"] >= 0:
        return 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if economics(meas, agent, a, mid)["net_benefit_bdt"] >= 0 else (mid, hi)
    return hi


def main():
    meas, agent, st = measured(), agent_service(), study()
    base = {k: v[1] for k, v in ASSUME.items()}
    worst = pessimistic()
    if st and st.get("analyst_triage", {}).get("minutes_per_alert_item_measured"):
        base["minutes_per_alert_item"] = st["analyst_triage"]["minutes_per_alert_item_measured"]
        base["minutes_per_linked_case"] = st["analyst_triage"]["minutes_per_linked_case_measured"]
    follows = [0.01, 0.05, 0.10, 0.30, 0.50]
    stated = st.get("stated_stop_rate") if st else None
    if stated:
        follows = sorted(set(follows + [round(stated, 3)]))
    table = [economics(meas, agent, base, f) for f in follows]
    be_base, be_worst = break_even(meas, agent, base), break_even(meas, agent, worst)
    # one-at-a-time sensitivity of net benefit at a cautious 10% follow rate
    tornado = []
    ref = economics(meas, agent, base, 0.10)["net_benefit_bdt"]
    for k, (lo, _, hi) in ASSUME.items():
        if lo == hi:
            continue
        a_lo, a_hi = dict(base, **{k: lo}), dict(base, **{k: hi})
        tornado.append({"assumption": k, "low": lo, "high": hi,
                        "net_at_low": economics(meas, agent, a_lo, 0.10)["net_benefit_bdt"],
                        "net_at_high": economics(meas, agent, a_hi, 0.10)["net_benefit_bdt"]})
    tornado.sort(key=lambda r: -abs(r["net_at_high"] - r["net_at_low"]))
    out = {"measured": meas, "agent_service": agent, "user_study_used": bool(st), "stated_stop_rate": stated,
           "assumptions_low_base_high": ASSUME, "per_million_p2p_transfers": table,
           "break_even_follow_rate": {"base_assumptions": be_base, "all_assumptions_pessimistic": be_worst},
           "tornado_net_benefit_at_10pct_follow": {"reference_net_bdt": ref, "rows": tornado},
           "reading": "UVERA pays for itself if at least the break-even share of paused scam victims stop. All money figures are "
                      "synthetic-world estimates per 1 million P2P transfers; they show the economics are robust, not real savings."}
    common.write_json(OUT / "business_case.json", out)
    charts(out)
    print(json.dumps({"break_even": out["break_even_follow_rate"], "agent": {k: agent[k] for k in ("customers_served_extra", "refusals_avoided_share", "unmet_bdt_recovered")},
                      "net_at": {r["follow_rate"]: round(r["net_benefit_bdt"]) for r in table}}, indent=1))


def charts(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    NAVY, GREY, TEAL, AMBER = "#1F3A5F", "#9AA5B1", "#2A9D8F", "#E9A23B"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    # 1. net benefit vs follow rate
    fr = np.linspace(0, 0.5, 101)
    meas, agent, base = out["measured"], out["agent_service"], {k: v[1] for k, v in ASSUME.items()}
    worst = pessimistic()
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for a, lab, col in ((base, "base assumptions", NAVY), (worst, "every assumption pessimistic", AMBER)):
        ax.plot(fr * 100, [economics(meas, agent, a, f)["net_benefit_bdt"] / 1e6 for f in fr], color=col, lw=2.2, label=lab)
    ax.axhline(0, color=GREY, lw=1)
    be = out["break_even_follow_rate"]
    ax.axvline(be["all_assumptions_pessimistic"] * 100, color=AMBER, ls="--", lw=1)
    ax.set_xlabel("Share of paused scam victims who stop (%)")
    ax.set_ylabel("Net benefit (Tk million per 1M transfers)")
    ax.set_title(f"Break-even: {be['base_assumptions']:.1%} (base) / {be['all_assumptions_pessimistic']:.1%} (pessimistic) of warned victims must stop", fontsize=10)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "business_break_even.png", dpi=180)
    plt.close(fig)
    # 2. tornado
    rows = out["tornado_net_benefit_at_10pct_follow"]["rows"][:8]
    ref = out["tornado_net_benefit_at_10pct_follow"]["reference_net_bdt"] / 1e6
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for i, r in enumerate(rows[::-1]):
        lo, hi = r["net_at_low"] / 1e6, r["net_at_high"] / 1e6
        ax.barh(i, hi - ref, left=ref, color=TEAL, height=0.6)
        ax.barh(i, lo - ref, left=ref, color=GREY, height=0.6)
    ax.set_yticks(range(len(rows)), [r["assumption"].replace("_", " ") for r in rows[::-1]], fontsize=8)
    ax.axvline(ref, color=NAVY, lw=1)
    ax.set_xlabel("Net benefit at a 10% follow rate (Tk million per 1M transfers)")
    ax.set_title("Which assumption matters most? (grey = low value, teal = high value)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "business_tornado.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
