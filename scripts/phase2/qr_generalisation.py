"""Phase-2: can QR Shield generalise better to a disguise family it never saw? (judges: "the 42.1% recall on the unseen QR
disguise family shows generalisation remains imperfect").

Honest protocol - family D stays unseen until the single test pass:
  1. leave-one-family-out on the KNOWN families A, B, C (train without F, score F's validation weeks vs honest weeks)
     selects the fusion weight between the supervised model and the unsupervised Isolation Forest;
  2. variant "+ ring signal": adds one generic AML collusion signal computed without labels - the largest share of a shop's
     weekly payers who also paid one other shop that week (shared counterparties) - to both components;
  3. one test pass on unseen merchants: recall per family at the phase-1 operating point (10% of honest validation weeks
     flagged), PR-AUC of D vs honest, weekly precision@20, honest false-positive rate.
Writes reports/phase2/qr_generalisation.json
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml import common  # noqa: E402
from uvera_ml.eval import metrics as M  # noqa: E402
from uvera_ml.features import qr as Q  # noqa: E402
from uvera_ml.models import ai5  # noqa: E402
from uvera_ml.sim.world import World  # noqa: E402

KNOWN = ["A_round_amount_atm", "B_split_under_limit", "C_cash_in_pass_through"]
D = ai5.HELD_OUT
WEIGHTS = [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]


def ring_signal(world, f: pd.DataFrame) -> pd.Series:
    ev = world.events[(world.events["etype"] == "qr_pay")][["src", "merchant_id", "day"]].copy()
    ev["week"] = ev["day"] // 7
    out = {}
    for wk, g in ev.groupby("week"):
        g = g.drop_duplicates(["src", "merchant_id"])
        mi, mcodes = pd.factorize(g["merchant_id"])
        pi, _ = pd.factorize(g["src"])
        A = sparse.csr_matrix((np.ones(len(g)), (mi, pi)), shape=(len(mcodes), pi.max() + 1))
        C = (A @ A.T).tocsr()
        n_payers = np.asarray(A.sum(1)).ravel()
        C.setdiag(0)
        C.eliminate_zeros()
        top = np.asarray(C.max(1).todense()).ravel()
        for m, t, n in zip(mcodes, top, n_payers):
            out[(m, wk)] = t / max(n, 1)
    return pd.Series([out.get((m, w), 0.0) for m, w in zip(f["merchant_id"], f["week"])], index=f.index)


class Shield(ai5.QRShield):
    def __init__(self, feats, w, seed=42):
        super().__init__(seed)
        self.feats, self.w = feats, w

    def fit(self, train, n_rounds=300):
        old = ai5.FEATURES
        ai5.FEATURES = self.feats
        try:
            return super().fit(train, n_rounds)
        finally:
            ai5.FEATURES = old

    def components(self, df):
        old = ai5.FEATURES
        ai5.FEATURES = self.feats
        try:
            return super().components(df)
        finally:
            ai5.FEATURES = old

    def score(self, df):
        c = self.components(df)
        return self.w * c["supervised"] + (1 - self.w) * c["isolation_forest"]


def lofo_select(tr, va, feats):
    rows = []
    for fam in KNOWN:
        tr_f = tr[tr["family"].fillna("legit") != fam]
        ev = va[(va["family"] == fam) | (va["is_disguised"] == 0)]
        if not (ev["family"] == fam).any():
            ev = tr[(tr["family"] == fam) | (tr["is_disguised"] == 0)]  # family absent from validation weeks
        m = Shield(feats, 0.5).fit(tr_f)
        comp = m.components(ev)
        y = (ev["family"] == fam).to_numpy().astype(int)
        for w in WEIGHTS:
            s = w * comp["supervised"] + (1 - w) * comp["isolation_forest"]
            rows.append({"held_out_family": fam, "w_supervised": w, "pr_auc_unseen": M.pr_auc(y, s)})
    df = pd.DataFrame(rows)
    mean = df.groupby("w_supervised")["pr_auc_unseen"].mean()
    return float(mean.idxmax()), df, mean.round(4).to_dict()


def test_pass(tr, va, te, feats, w):
    m = Shield(feats, w).fit(tr)
    s_val, s_te = m.score(va), m.score(te)
    amber = float(np.quantile(s_val[va["is_disguised"].to_numpy() == 0], 0.90))
    flagged = s_te > amber
    y = te["is_disguised"].to_numpy()
    d = (te["family"] == D).to_numpy()
    seen = ~d
    rec = {fam: float(flagged[(te["family"] == fam).to_numpy()].mean()) for fam in KNOWN + [D]}
    return {"w_supervised": w, "recall_by_family": rec,
            "recall_known_families_mean": float(np.mean([rec[f] for f in KNOWN])),
            "pr_auc_D_vs_honest": M.pr_auc(np.r_[np.ones(d.sum()), np.zeros((y == 0).sum())], np.r_[s_te[d], s_te[y == 0]]),
            "pr_auc_seen_families": M.pr_auc(y[seen], s_te[seen]),
            "weekly_precision_at_20": ai5._weekly_precision_at_k(te.reset_index(drop=True), s_te, 20),
            "fpr_honest": float(flagged[y == 0].mean())}


if __name__ == "__main__":
    t0 = time.time()
    world = World.load(ROOT / "_outputs" / "world_full")
    f = Q.build_qr_features(world)
    f["split"] = ai5.assign_qr_split(f, world.n_days)
    f["shared_payer_share"] = ring_signal(world, f)
    tr, va, te = (f[f["split"] == s].reset_index(drop=True) for s in ("train", "val", "test"))
    print("built", len(f), "merchant-weeks in", round(time.time() - t0), "s", flush=True)
    base_feats = list(Q.FEATURES)
    ring_feats = base_feats + ["shared_payer_share"]
    out = {"protocol": __doc__.strip().splitlines()[0], "variants": []}
    out["variants"].append({"name": "Phase 1 (fixed 70/30 fusion)", "selection": "design choice", **test_pass(tr, va, te, base_feats, 0.7)})
    w1, rows1, mean1 = lofo_select(tr, va, base_feats)
    out["variants"].append({"name": "LOFO-selected fusion weight", "selection": mean1, **test_pass(tr, va, te, base_feats, w1)})
    w2, rows2, mean2 = lofo_select(tr, va, ring_feats)
    out["variants"].append({"name": "LOFO-selected fusion + shared-payer ring signal", "selection": mean2,
                            **test_pass(tr, va, te, ring_feats, w2)})
    out["lofo_rows"] = {"base": rows1.to_dict("records"), "ring": rows2.to_dict("records")}
    sub = f[(f["family"] == D) | (f["is_disguised"] == 0)]
    out["ring_signal_auc_D_vs_honest_all_weeks"] = M.roc_auc((sub["family"] == D).astype(int), sub["shared_payer_share"])
    common.write_json(ROOT / "reports" / "phase2" / "qr_generalisation.json", out)
    for v in out["variants"]:
        print(v["name"], "w=", v["w_supervised"], "D recall", round(v["recall_by_family"][D], 3), "known", round(v["recall_known_families_mean"], 3),
              "P@20", round(v["weekly_precision_at_20"], 3), "fpr", round(v["fpr_honest"], 3), flush=True)
    print("done in", round(time.time() - t0), "s")
