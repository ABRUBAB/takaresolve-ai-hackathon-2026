"""Phase-2: QR Shield with a human feedback loop, and QR Shield's value inside the scam chain.

1. Few-shot analyst feedback: analysts review the weekly top-20 list; when they confirm a few shops of a NEW disguise style,
   those confirmed shop-weeks become training labels. We add k = 0, 3, 5, 10, 20 confirmed family-D shop-weeks taken from the
   weeks BEFORE the test window (never test merchants) and measure recall on family D in the test (unseen merchants).
2. Interception value: of the scam money that mules cash out through QR payments in the test window, how much passes through
   shops that QR Shield flags (the points where an analyst can intervene)?
Writes reports/phase2/qr_feedback.json
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml import common  # noqa: E402
from uvera_ml.eval import metrics as M  # noqa: E402
from uvera_ml.features import qr as Q  # noqa: E402
from uvera_ml.features.splits import is_test_entity  # noqa: E402
from uvera_ml.models import ai5  # noqa: E402
from uvera_ml.sim.world import World  # noqa: E402

D = ai5.HELD_OUT


def main():
    world = World.load(ROOT / "_outputs" / "world_full")
    f = Q.build_qr_features(world)
    f["split"] = ai5.assign_qr_split(f, world.n_days)
    tr, va, te = (f[f["split"] == s].reset_index(drop=True) for s in ("train", "val", "test"))
    # pool of analyst-confirmable D shop-weeks: before the test window, merchants NOT in the test group
    pool = f[(f["family"] == D) & ~is_test_entity(f["merchant_id"]) & (f["week"] * 7 + 3 < 100)].sample(frac=1, random_state=7)
    rows = []
    for k in (0, 3, 5, 10, 20):
        add = pool.head(k)
        m = ai5.QRShield(42).fit(pd.concat([tr, add], ignore_index=True))
        s_val, s_te = m.score(va), m.score(te)
        amber = float(np.quantile(s_val[va["is_disguised"].to_numpy() == 0], 0.90))
        flagged = s_te > amber
        y = te["is_disguised"].to_numpy()
        rec = {fam: float(flagged[(te["family"] == fam).to_numpy()].mean()) for fam in
               ["A_round_amount_atm", "B_split_under_limit", "C_cash_in_pass_through", D]}
        rows.append({"confirmed_D_examples_added": int(len(add)), "recall_by_family": rec,
                     "weekly_precision_at_20": ai5._weekly_precision_at_k(te, s_te, 20), "fpr_honest": float(flagged[y == 0].mean())})
        print(rows[-1], flush=True)
    # interception: scam money cashed out via QR in the test window
    ms = pd.read_parquet(ROOT / "artifacts" / "ai5" / "merchant_scores.parquet")
    flagged_m = set(ms.loc[ms["state"] != "green", "merchant_id"])
    ev = world.events
    qr_scam = ev[(ev["mule_flow"] == 1) & (ev["etype"] == "qr_pay") & (ev["day"] >= 100)]
    tested = qr_scam[qr_scam["merchant_id"].isin(set(ms["merchant_id"]))]
    out = {"few_shot_feedback": rows, "pool_size": int(len(pool)),
           "interception": {"scam_qr_cashout_events_test_window": int(len(tested)),
                            "scam_qr_cashout_bdt": float(tested["amount"].sum()),
                            "share_of_events_through_flagged_shops": float(tested["merchant_id"].isin(flagged_m).mean()) if len(tested) else None,
                            "share_of_money_through_flagged_shops": float(tested.loc[tested["merchant_id"].isin(flagged_m), "amount"].sum()
                                                                         / max(1.0, tested["amount"].sum())),
                            "note": "test merchants only (unseen merchants scored by the deployed QR Shield)"}}
    common.write_json(ROOT / "reports" / "phase2" / "qr_feedback.json", out)
    print(out["interception"])


if __name__ == "__main__":
    main()
