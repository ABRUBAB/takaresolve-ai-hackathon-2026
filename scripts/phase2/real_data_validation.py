"""Phase-2: validate on REAL public data we did not create.

1. BTTC (Mendeley Data, CC BY 4.0, 2026): real Bangla SMS/Telegram messages labelled SPAM (fraud, phishing, gambling, fake
   prizes), PROMO and HAM (incl. bank/MFS notices).
   a) zero-shot: the served AI-2 model (trained only on synthetic text) on real messages;
   b) pilot simulation: the same AI-2 architecture (character TF-IDF + logistic regression) trained with n real labelled
      messages (+ our synthetic corpus) and tested on held-out real messages (5 seeds, exact duplicates removed and kept on
      one side only).
2. PaySim (Lopez-Rojas et al. 2016; a mobile-money simulator calibrated on one month of real logs of an African MFS):
   the AI-1 method (LightGBM + isotonic calibration, thresholds from validation, one test pass on later hours and unseen
   senders) vs a rule, on independent mobile-money data.
Writes reports/phase2/real_data_validation.json
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT.parent / "external_data"
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml import common  # noqa: E402
from uvera_ml.eval import metrics as M  # noqa: E402
from uvera_ml.models.ai2 import tfidf_lr  # noqa: E402
from uvera_ml.serving.store import ArtifactStore  # noqa: E402
from uvera_ml.serving.text import TextEngine  # noqa: E402


def bttc():
    d = pd.read_parquet(EXT / "BTTC_complete_rows.parquet")
    d["text"] = d["Text_Clean"].fillna(d["Text"]).astype(str).str.strip()
    d = d[d["text"].str.len() > 3].drop_duplicates("text").reset_index(drop=True)
    y_spam = (d["Label"] == "SPAM").to_numpy().astype(int)
    eng = TextEngine(ArtifactStore([ROOT]))
    p = np.asarray(eng.scam_prob(d["text"].tolist()))
    ham, promo = (d["Label"] == "HAM").to_numpy(), (d["Label"] == "PROMO").to_numpy()
    zero = {"messages_after_dedup": int(len(d)), "spam": int(y_spam.sum()), "ham": int(ham.sum()), "promo": int(promo.sum()),
            "pr_auc_spam_vs_ham": M.pr_auc(y_spam[~promo], p[~promo]), "pr_auc_spam_vs_ham_and_promo": M.pr_auc(y_spam, p),
            "spam_caught_at_0.5": float((p[y_spam == 1] >= 0.5).mean()), "ham_flagged_at_0.5": float((p[ham] >= 0.5).mean()),
            "promo_flagged_at_0.5": float((p[promo] >= 0.5).mean())}
    print("zero-shot", zero, flush=True)
    syn = pd.read_parquet(ROOT / "artifacts" / "ai2" / "corpus.parquet")
    syn_y = (syn["label"] != "legit").astype(int).to_numpy()
    curve = []
    for n in (0, 100, 300, 1000, 3000):
        res = {"real_training_messages": n, "real_only": [], "synthetic_plus_real": []}
        for seed in range(5):
            rng = np.random.default_rng(seed)
            idx = rng.permutation(len(d))
            test, pool = idx[: len(d) // 2], idx[len(d) // 2:]
            tr = pool[:n]
            yt = y_spam[test]
            if n >= 50 and len(set(y_spam[tr])) == 2:
                m = tfidf_lr().fit(d["text"].iloc[tr], y_spam[tr])
                res["real_only"].append(M.pr_auc(yt, m.predict_proba(d["text"].iloc[test])[:, 1]))
            X = pd.concat([syn["text"], d["text"].iloc[tr]], ignore_index=True)
            Y = np.r_[syn_y, y_spam[tr]]
            m2 = tfidf_lr().fit(X, Y)
            res["synthetic_plus_real"].append(M.pr_auc(yt, m2.predict_proba(d["text"].iloc[test])[:, 1]))
        res = {k: (float(np.mean(v)) if isinstance(v, list) and v else v) for k, v in res.items()}
        res["base_rate"] = float(y_spam.mean())
        curve.append(res)
        print("curve", res, flush=True)
    return {"dataset": "BTTC - Bangla Telegram and Text Communications (Mendeley Data, CC BY 4.0, 2026)",
            "note": "10,267 complete rows (the download cut the last 15 rows); exact duplicates removed",
            "zero_shot_served_model": zero, "pilot_learning_curve": curve}


def paysim():
    files = sorted(EXT.glob("paysim_*.parquet"))
    if len(files) < 2:
        return None
    import lightgbm as lgb
    from uvera_ml.uncertainty.calibration import IsotonicCalibrator
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df[df["type"].isin(["TRANSFER", "CASH_OUT"])].reset_index(drop=True)  # PaySim fraud happens only in these types
    df = df.sort_values("step").reset_index(drop=True)
    # behaviour features known before the transaction (no post-transaction balances: the PaySim authors warn they leak)
    df["is_transfer"] = (df["type"] == "TRANSFER").astype(int)
    df["amount_log"] = np.log1p(df["amount"])
    df["amount_to_balance"] = df["amount"] / (df["oldbalanceOrg"] + 1)
    df["drains_account"] = (df["amount"] >= df["oldbalanceOrg"] * 0.99).astype(int)
    df["hour"] = df["step"] % 24
    df["dest_prior_in"] = df.groupby("nameDest").cumcount()
    df["dest_is_merchant"] = df["nameDest"].str.startswith("M").astype(int)
    df["dest_empty_before"] = (df["oldbalanceDest"] == 0).astype(int)
    feats = ["is_transfer", "amount_log", "amount_to_balance", "drains_account", "hour", "dest_prior_in", "dest_is_merchant",
             "dest_empty_before"]
    y = df["isFraud"].to_numpy()
    t = df["step"].to_numpy()
    tr, va, te = t < 400, (t >= 400) & (t < 500), t >= 500   # time-ordered: train / validation / later test hours
    params = dict(objective="binary", learning_rate=0.05, num_leaves=31, min_child_samples=40, feature_fraction=0.8,
                  bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=42)
    b = lgb.train(params, lgb.Dataset(df.loc[tr, feats], y[tr]), 400)
    s_va, s_te = b.predict(df.loc[va, feats]), b.predict(df.loc[te, feats])
    cal = IsotonicCalibrator().fit(s_va, y[va])
    p_te = cal.predict(s_te)
    rule = (df["amount"] >= 200_000).to_numpy()[te].astype(float) + df.loc[te, "amount"].to_numpy() / 1e9  # PaySim's own flag rule
    at = M.at_alert_rate(y[te], p_te, 0.05, df.loc[te, "amount"].to_numpy())
    rat = M.at_alert_rate(y[te], rule, 0.05, df.loc[te, "amount"].to_numpy())
    out = {"dataset": "PaySim (Lopez-Rojas, Elmir, Axelsson 2016), Kaggle release, TRANSFER + CASH_OUT rows",
           "rows_used": int(len(df)), "fraud_rows": int(y.sum()), "test_rows": int(te.sum()), "test_fraud": int(y[te].sum()),
           "features": feats, "split": "time-ordered: hours 0-399 train, 400-499 validation (calibration), 500+ test",
           "model": {"pr_auc": M.pr_auc(y[te], p_te), "roc_auc": M.roc_auc(y[te], p_te), "ece": M.ece(y[te], p_te),
                     "recall_at_5pct_alerts": at["recall"], "fraud_money_caught_at_5pct": at.get("amount_caught")},
           "rule_amount_over_200k": {"pr_auc": M.pr_auc(y[te], rule), "recall_at_5pct_alerts": rat["recall"]}}
    print("paysim", out, flush=True)
    return out


def main():
    out = {"bttc": bttc(), "paysim": paysim()}
    common.write_json(ROOT / "reports" / "phase2" / "real_data_validation.json", out)


if __name__ == "__main__":
    main()
