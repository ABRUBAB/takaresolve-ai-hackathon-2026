"""AI-2 live Scam Text Check (TF-IDF model served; falls back to a quick in-process model if artifacts are missing)."""
from __future__ import annotations

import re

import numpy as np

from uvera_ml.serving.store import ArtifactStore
from uvera_ml.sim.text import CLASSES
from uvera_ml.uncertainty.calibration import IsotonicCalibrator
from uvera_ml.xai.occlusion import occlusion

LEGIT = CLASSES.index("legit")
FAMILY_TEXT = {
    "otp_reversal_counter": ("'Money sent by mistake / tell me the code' trick", "'ভুলে টাকা গেছে / কোডটা বলুন' প্রতারণা"),
    "fake_customer_care": ("Fake customer care asking for PIN or code", "ভুয়া কাস্টমার কেয়ার, পিন বা কোড চাইছে"),
    "prize_lottery": ("Fake prize that asks for a fee", "ফি চাওয়া ভুয়া পুরস্কার"),
    "investment_group": ("'Guaranteed profit' investment offer", "'নিশ্চিত লাভ' বিনিয়োগের প্রস্তাব"),
    "gold_jar_offer": ("Hidden treasure / ritual money request", "গুপ্তধন / অনুষ্ঠানের টাকা চাওয়া"),
    "refund_government": ("Fake government allowance needing a fee", "ফি চাওয়া ভুয়া সরকারি ভাতা"),
    "legit": ("Looks like a normal message", "সাধারণ বার্তার মতো"),
}
INJECTION_RE = re.compile(r"ignore (all )?(previous|prior) instructions|system:|you are now|ভুলে যাও|instruction bhule", re.I)


class TextEngine:
    def __init__(self, store: ArtifactStore):
        self.source = store.source_of("ai2")
        self.model, self.calib = None, None
        info = store.json("artifacts/ai2/model_info.json", {}) or {}
        p = store.path("artifacts/ai2/tfidf_lr.joblib")
        if p is not None:
            try:
                import joblib

                self.model = joblib.load(p)
                cal = (info.get("verdict_calibrators") or {}).get("tfidf_lr")
                self.calib = IsotonicCalibrator.from_json(cal) if cal else None
            except Exception as e:  # noqa: BLE001 - e.g. scikit-learn version mismatch
                print("AI-2 artifact could not be loaded, training a fallback:", repr(e)[:160])
                self.model = None
        if self.model is None:
            self._train_fallback(store)
        self.version = f"ai2-tfidf-lr-{self.source}"

    def _train_fallback(self, store: ArtifactStore) -> None:
        from uvera_ml.models.ai2 import tfidf_lr
        from uvera_ml.sim.text import template_corpus

        corpus = store.parquet("artifacts/ai2/corpus.parquet")
        if corpus is None:
            corpus = template_corpus(per_template=40)
        y = corpus["label"].map({c: i for i, c in enumerate(CLASSES)}).to_numpy()
        self.model = tfidf_lr().fit(corpus["text"], y)
        self.source = self.source + "+fallback"

    def raw_scam_prob(self, texts: list[str]) -> np.ndarray:
        return 1 - self.model.predict_proba(texts)[:, LEGIT]

    def scam_prob(self, texts: list[str]) -> np.ndarray:
        p = self.raw_scam_prob(texts)
        p = self.calib.predict(p) if self.calib else p
        return np.clip(p, 0.02, 0.98)  # an estimate is never shown as 0% or 100%

    def check(self, text: str) -> dict:
        text = text.strip()[:1000]
        pr = self.model.predict_proba([text])[0]
        p = float(self.scam_prob([text])[0])
        order = np.argsort(-pr)
        fam = CLASSES[int(order[0])] if order[0] != LEGIT or p < 0.5 else CLASSES[int(order[1])]
        state = "likely_scam" if p >= 0.7 else "likely_safe" if p <= 0.3 else "unsure"
        en, bn = FAMILY_TEXT.get(fam, (fam, fam))
        return {
            "model_version": self.version, "p_scam": p, "state": state,
            "family": fam if state != "likely_safe" else "legit", "family_text_en": en if state != "likely_safe" else FAMILY_TEXT["legit"][0],
            "family_text_bn": bn if state != "likely_safe" else FAMILY_TEXT["legit"][1],
            "top_families": [{"family": CLASSES[int(i)], "probability": float(pr[i])} for i in order[:3]],
            "highlights": occlusion(text, self.raw_scam_prob) if state != "likely_safe" else [],
            "contains_ai_instructions": bool(INJECTION_RE.search(text)),
            "note": "Model estimate on synthetic training data. If you are unsure, do not send money and contact the provider.",
        }
