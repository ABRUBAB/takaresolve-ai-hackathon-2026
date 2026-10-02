"""AI-2 Scam Text Sentinel: is a pasted message a scam, which family, and how sure are we?

Models (compared honestly): TF-IDF char n-grams + LR  |  BGE-M3 embeddings + LR  |  BGE-M3 + evidential head.
Validation: StratifiedGroupKFold on style family A (groups = template / generation batch); test = held-out style
family B; external sanity test = UCI SMS Spam Collection (English).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline

from uvera_ml.common import write_json
from uvera_ml.eval import metrics as M
from uvera_ml.eval import plots
from uvera_ml.sim.text import CLASSES
from uvera_ml.uncertainty.calibration import IsotonicCalibrator
from uvera_ml.uncertainty.evidential import EvidentialHead
from uvera_ml.xai.occlusion import occlusion

LEGIT_IDX = CLASSES.index("legit")


def tfidf_lr():
    return make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=200_000),
                         LogisticRegression(C=4.0, max_iter=3000, class_weight="balanced"))


class Embedder:
    """BGE-M3 (BAAI/bge-m3, MIT) via sentence-transformers; falls back to TF-IDF + SVD when unavailable."""

    def __init__(self, use_bge: bool = True):
        self.kind = "tfidf_svd_fallback"
        self.error = None if use_bge else "BGE-M3 disabled by the caller"
        if use_bge:
            try:
                import torch
                from sentence_transformers import SentenceTransformer

                dev = "cuda" if torch.cuda.is_available() else "cpu"
                self.model = SentenceTransformer("BAAI/bge-m3", device=dev)
                if dev == "cuda":
                    self.model.half()
                self.kind = "bge-m3"
            except Exception as e:  # noqa: BLE001
                self.error = repr(e)[:300]
                print("BGE-M3 unavailable, using TF-IDF+SVD fallback:", self.error)

    def fit(self, texts):
        if self.kind != "bge-m3":
            self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=100_000)
            self.svd = TruncatedSVD(256, random_state=42).fit(self.vec.fit_transform(texts))
        return self

    def encode(self, texts) -> np.ndarray:
        texts = list(texts)
        if self.kind == "bge-m3":
            return self.model.encode(texts, batch_size=64, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        Z = self.svd.transform(self.vec.transform(texts))
        return Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)


def _verdict(proba: np.ndarray) -> np.ndarray:
    return 1 - proba[:, LEGIT_IDX]


def _metrics(y_cls, proba, p_scam, conf, name) -> dict:
    y_bin = (y_cls != LEGIT_IDX).astype(int)
    pred = proba.argmax(1)
    correct = (pred == y_cls).astype(float)
    rc = M.risk_coverage(correct, conf)
    return {"model": name, "macro_f1": float(f1_score(y_cls, pred, average="macro")),
            "verdict_pr_auc": M.pr_auc(y_bin, p_scam), "verdict_roc_auc": M.roc_auc(y_bin, p_scam),
            "verdict_ece": M.ece(y_bin, p_scam), "verdict_brier": M.brier(y_bin, p_scam),
            "error_at_100pct": float(rc["risk"].iloc[-1]),
            "error_at_80pct": float(rc.loc[(rc["coverage"] - 0.8).abs().idxmin(), "risk"]),
            "uncertainty_flags_errors_auroc": M.roc_auc(1 - correct, -conf) if 0 < correct.sum() < len(correct) else None}


def run_ai2(out: str | Path, corpus: pd.DataFrame, uci: pd.DataFrame | None = None, use_bge: bool = True,
            seeds=(42, 7, 1337), quick: bool = False, diagnostics: dict | None = None) -> dict:
    out = Path(out)
    art, rep = out / "artifacts" / "ai2", out / "reports"
    art.mkdir(parents=True, exist_ok=True)
    (rep / "figures").mkdir(parents=True, exist_ok=True)
    corpus = corpus.copy()
    corpus["y"] = corpus["label"].map({c: i for i, c in enumerate(CLASSES)})
    pool = corpus[corpus["family"] == "A"].reset_index(drop=True)
    test = corpus[corpus["family"] == "B"].reset_index(drop=True)
    print("pool", len(pool), "test (held-out style B)", len(test), pool["source"].value_counts().to_dict())

    emb = Embedder(use_bge).fit(pool["text"])
    Xp, Xt = emb.encode(pool["text"]), emb.encode(test["text"])
    yp, yt = pool["y"].to_numpy(), test["y"].to_numpy()

    # ---- cross-validation on the pool (grouped by template / generation batch)
    oof = {m: np.zeros((len(pool), len(CLASSES))) for m in ("tfidf_lr", "emb_lr", "emb_evidential")}
    oof_u = np.zeros(len(pool))
    cv_rows = []
    for seed in (seeds[:1] if quick else seeds):
        cv = StratifiedGroupKFold(n_splits=3 if quick else 5, shuffle=True, random_state=seed)
        for fold, (a, b) in enumerate(cv.split(pool, yp, pool["group"])):
            m1 = tfidf_lr().fit(pool["text"].iloc[a], yp[a])
            p1 = m1.predict_proba(pool["text"].iloc[b])
            m2 = LogisticRegression(C=2.0, max_iter=3000, class_weight="balanced").fit(Xp[a], yp[a])
            p2 = m2.predict_proba(Xp[b])
            m3 = EvidentialHead(len(CLASSES), epochs=15 if quick else 40, seed=seed).fit(Xp[a], yp[a])
            p3, u3 = m3.predict(Xp[b])
            for name, pr in (("tfidf_lr", p1), ("emb_lr", p2), ("emb_evidential", p3)):
                cv_rows.append({"model": name, "seed": seed, "fold": fold, "macro_f1": float(f1_score(yp[b], pr.argmax(1), average="macro")),
                                "verdict_pr_auc": M.pr_auc((yp[b] != LEGIT_IDX).astype(int), _verdict(pr))})
                if seed == seeds[0]:
                    oof[name][b] = pr
            if seed == seeds[0]:
                oof_u[b] = u3
    cv_df = pd.DataFrame(cv_rows)
    cv_summary = cv_df.groupby("model")[["macro_f1", "verdict_pr_auc"]].agg(["mean", "std"]).round(4)
    cv_summary.columns = ["_".join(c) for c in cv_summary.columns]
    served = str(cv_summary["verdict_pr_auc_mean"].idxmax())  # chosen on CV, never on the test set

    # ---- final models on the whole pool; verdict calibrators fitted on out-of-fold predictions
    y_bin_pool = (yp != LEGIT_IDX).astype(int)
    final = {"tfidf_lr": tfidf_lr().fit(pool["text"], yp),
             "emb_lr": LogisticRegression(C=2.0, max_iter=3000, class_weight="balanced").fit(Xp, yp),
             "emb_evidential": EvidentialHead(len(CLASSES), epochs=15 if quick else 40, seed=seeds[0]).fit(Xp, yp)}
    calib = {m: IsotonicCalibrator().fit(_verdict(oof[m]), y_bin_pool) for m in final}
    u_thr = float(np.quantile(oof_u, 0.9))

    def predict(name, texts, X):
        if name == "tfidf_lr":
            pr = final[name].predict_proba(texts)
            return pr, pr.max(1)
        if name == "emb_lr":
            pr = final[name].predict_proba(X)
            return pr, pr.max(1)
        pr, u = final[name].predict(X)
        return pr, 1 - u

    test_rows, preds = [], {}
    for name in final:
        pr, conf = predict(name, test["text"], Xt)
        p_scam = calib[name].predict(_verdict(pr))
        preds[name] = (pr, p_scam, conf)
        test_rows.append(_metrics(yt, pr, p_scam, conf, name))
    by_lang = {}
    pr, p_scam, _ = preds[served]
    for lang, idx in test.groupby("language").indices.items():
        yb = (yt[idx] != LEGIT_IDX).astype(int)
        by_lang[lang] = {"n": int(len(idx)), "verdict_pr_auc": M.pr_auc(yb, p_scam[idx]),
                         "verdict_f1_at_0.5": float(f1_score(yb, (p_scam[idx] >= 0.5).astype(int)))}
    external = None
    if uci is not None and len(uci):
        Xu = emb.encode(uci["text"])
        external = {}
        for name in final:
            pr_u, _ = predict(name, uci["text"], Xu)
            external[name] = {"n": int(len(uci)), "spam_share": float(uci["label"].mean()),
                              "verdict_pr_auc": M.pr_auc(uci["label"], calib[name].predict(_verdict(pr_u)))}

    # ---- examples with faithful phrase highlights (served model)
    def scam_prob(texts):
        Xe = emb.encode(texts) if served != "tfidf_lr" else None
        p, _ = predict(served, texts, Xe)
        return calib[served].predict(_verdict(p))

    examples = []
    for i in test.sample(min(12, len(test)), random_state=1).index:
        examples.append({"text": test.at[i, "text"], "true": test.at[i, "label"], "language": test.at[i, "language"],
                         "p_scam": float(p_scam[i]), "predicted_family": CLASSES[int(pr[i].argmax())],
                         "highlights": occlusion(test.at[i, "text"], scam_prob)})

    plots.reliability({f"{served} (calibrated)": M.reliability_table((yt != LEGIT_IDX).astype(int), p_scam)},
                      rep / "figures" / "ai2_reliability.png", "AI-2 verdict calibration (held-out style B)")

    # ---- export
    import joblib
    import sklearn

    joblib.dump(final["tfidf_lr"], art / "tfidf_lr.joblib")
    np.savez_compressed(art / "emb_lr.npz", coef=final["emb_lr"].coef_, intercept=final["emb_lr"].intercept_)
    final["emb_evidential"].save(str(art / "emb_evidential.pt"))
    write_json(art / "model_info.json", {"classes": CLASSES, "served_model": served, "embedder": emb.kind,
                                         "sklearn_version": sklearn.__version__, "evidential_u_threshold_90pct": u_thr,
                                         "verdict_calibrators": {m: c.to_json() for m, c in calib.items()},
                                         "states": {"likely_scam": "p_scam >= 0.7", "likely_safe": "p_scam <= 0.3",
                                                    "unsure": "otherwise, or evidential u above threshold"}})
    corpus.to_parquet(art / "corpus.parquet", index=False)
    summary = {"ai": "AI-2 Scam Text Sentinel", "embedder": emb.kind, "served_model_chosen_on_cv": served,
               "diagnostics": {"embedder": emb.kind, "embedder_error": emb.error,
                               "intended_pipeline_ran": emb.kind == "bge-m3" and bool((corpus["source"] == "gemini").any()),
                               **(diagnostics or {})},
               "corpus": {"total": int(len(corpus)), "by_source": corpus["source"].value_counts().to_dict(),
                          "by_language": corpus["language"].value_counts().to_dict(), "by_label": corpus["label"].value_counts().to_dict()},
               "cv_summary_family_A": cv_summary.reset_index().to_dict("records"),
               "test_heldout_style_B": test_rows, "test_by_language_served": by_lang,
               "external_uci_sms_spam": external, "examples": examples}
    write_json(rep / "metrics_ai2.json", summary)
    cv_df.to_csv(rep / "ai2_cv_folds.csv", index=False)
    print(json.dumps({"served": served, "test": test_rows}, indent=1, default=float)[:1500])
    return summary
