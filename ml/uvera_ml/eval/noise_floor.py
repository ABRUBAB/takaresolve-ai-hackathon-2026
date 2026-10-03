"""How good can an AI-4 forecast possibly be? A perfect-knowledge forecaster, simulated.

The synthetic world's cash-out rule is known (uvera_ml/sim/world.py): every active customer with more than Tk 400 cashes
out with probability 0.10 (app) or 0.16 (USSD), halved for daily-wage earners and x1.8 on festival days; the amount is
20-70% of the balance rounded to Tk 100, paid at the home agent (80%) or a random agent in the same zone (20%). Mule
cash-outs come on top.

The forecaster simulated here knows every customer's balance at the moment of the decision and every mule cash-out,
which no real forecaster made days ahead can know. It replays each day's coin flips many times and forecasts the
10/50/90% quantiles of the result. Its remaining error is pure chance: no model, feature or amount of compute can beat it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from uvera_ml import forecast as F

ZONE_SHARE_HOME = 0.8  # world.py: 80% of cash-outs at the home agent, the rest at a random agent in the same zone


def agent_cashout_floor(world, sims: int = 300, seed: int = 7) -> dict:
    """Per split ('val', 'test'): MASE, pinball, 80% coverage of the perfect-knowledge forecaster (as F.evaluate)."""
    rng = np.random.default_rng(seed)
    cu = world.customers.reset_index(drop=True)
    mule = world.truth_customers.set_index("customer_id").loc[cu["customer_id"], "is_mule"].to_numpy()
    agents = world.agents.reset_index(drop=True)
    n_agents = len(agents)
    aidx = {a: i for i, a in enumerate(agents["agent_id"])}
    home = cu["home_agent"].map(aidx).to_numpy()
    zone_members = {z: np.where(agents["zone"].to_numpy() == z)[0] for z in agents["zone"].unique()}
    czone = cu["zone"].to_numpy()
    rate = np.where(cu["channel"] == "app", 0.10, 0.16) * np.where(cu["segment"] == "daily_wage", 0.5, 1.0)
    fest = set(range(world.meta["festival_days"][0], world.meta["festival_days"][1] + 1))

    ev = world.events
    co = ev[(ev["etype"] == "cash_out") & (ev["src_kind"] == 0)]
    normal = co[co["mule_flow"] == 0].groupby(["src", "day"])["amount"].sum()
    mules = co[co["mule_flow"] == 1].groupby(["agent_id", "day"])["amount"].sum()
    eod = world.daily_customer.pivot(index="customer_id", columns="day", values="balance_eod").reindex(cu["customer_id"])
    series = F.agent_series(world)

    def day_quantiles(d: int) -> pd.DataFrame:
        own = normal.xs(d, level="day") if d in normal.index.get_level_values("day") else pd.Series(dtype=float)
        bal = eod[d].fillna(0).to_numpy(float) + cu["customer_id"].map(own).fillna(0).to_numpy()  # balance before cash-out
        ok = np.where((bal > 400) & ~mule)[0]
        p = rate[ok] * (1.8 if d in fest else 1.0)
        demand = np.zeros((sims, n_agents))
        for s in range(sims):
            hit = ok[rng.random(len(ok)) < p]
            amt = np.minimum(np.maximum(100, np.round(bal[hit] * rng.uniform(0.2, 0.7, len(hit)) / 100) * 100), bal[hit])
            ag = home[hit].copy()
            away = rng.random(len(hit)) >= ZONE_SHARE_HOME
            for z, members in zone_members.items():
                sel = away & (czone[hit] == z)
                ag[sel] = members[rng.integers(0, len(members), sel.sum())]
            demand[s] = np.bincount(ag, weights=amt, minlength=n_agents)
        m = mules.xs(d, level="day") if d in mules.index.get_level_values("day") else pd.Series(dtype=float)
        demand += agents["agent_id"].map(m).fillna(0).to_numpy()[None, :]
        q = np.quantile(demand, [0.1, 0.5, 0.9], axis=0)
        return pd.DataFrame({"id": agents["agent_id"], "day": d, "q0.1": q[0], "q0.5": q[1], "q0.9": q[2]})

    org = F.origins(world.n_days)
    out = {}
    for split in ("val", "test"):
        rows = [F.evaluate(series, pd.concat([day_quantiles(d) for d in range(o, o + F.HORIZON)], ignore_index=True), o)
                for o in org[split]]
        r = pd.DataFrame(rows)
        out[split] = {k: float(r[k].mean()) for k in ("mase", "pinball_mean", "coverage_80")}
    out["method"] = (f"{sims} simulated replays of each day's cash-outs with every balance and mule cash-out known "
                     "(impossible in practice): a lower bound on any forecaster's error")
    return out


def share_of_possible_gain(baseline: float, model: float, floor: float) -> float | None:
    """How much of the gap between the baseline and the perfect-knowledge floor the model closes (1.0 = all of it)."""
    gap = baseline - floor
    return float((baseline - model) / gap) if gap > 0 else None
