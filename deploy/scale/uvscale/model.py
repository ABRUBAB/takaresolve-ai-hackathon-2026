"""Model loading for the scorer: verify artifacts against the manifest, then load AI-1 (+ AI-2) without the world.

Only small artifacts are read (LightGBM text model, isotonic/conformal/novelty/threshold JSON, AI-2 TF-IDF+LR).
The decision policy and reason texts are imported from uvera_ml so the stack uses exactly the same rules as the API.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import lightgbm as lgb
import numpy as np
import yaml

from uvscale.online_features import FEATURES

ROOT = Path(os.environ.get("UVERA_ROOT", "/repo"))
AI1_FILES = ["artifacts/ai1/model.txt", "artifacts/ai1/calibrator.json", "artifacts/ai1/conformal.json",
             "artifacts/ai1/novelty.json", "artifacts/ai1/thresholds.json", "artifacts/ai1/features.json"]
AI2_FILES = ["artifacts/ai2/tfidf_lr.joblib", "artifacts/ai2/model_info.json"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(files: list[str]) -> dict:
    """SHA-256 of every served file vs artifacts/manifest.json. A mismatch refuses to serve (fail closed)."""
    manifest = json.loads((ROOT / "artifacts" / "manifest.json").read_text(encoding="utf-8"))
    expected = {a["path"]: a for a in manifest["artifacts"]}
    rows = []
    for rel in files:
        got = sha256(ROOT / rel)
        exp = expected.get(rel, {})
        rows.append({"path": rel, "sha256": got, "expected": exp.get("sha256"), "ok": got == exp.get("sha256"),
                     "code_commit": exp.get("code_commit"), "notebook": exp.get("notebook")})
    registry = None
    reg_path = ROOT / "artifacts" / "registry.json"
    if reg_path.exists():
        try:
            registry = json.loads(reg_path.read_text(encoding="utf-8"))
        except ValueError:
            registry = {"error": "registry.json unreadable"}
    return {"manifest_version": manifest.get("version"), "data_version": manifest.get("data_version"),
            "files": rows, "all_ok": all(r["ok"] for r in rows), "registry_present": registry is not None}


class PauseModel:
    def __init__(self):
        self.verification = verify(AI1_FILES)
        if not self.verification["all_ok"] and os.environ.get("ALLOW_UNVERIFIED", "0") != "1":
            bad = [r["path"] for r in self.verification["files"] if not r["ok"]]
            raise RuntimeError(f"artifact checksum mismatch vs manifest: {bad}")
        j = lambda rel: json.loads((ROOT / rel).read_text(encoding="utf-8"))  # noqa: E731
        self.booster = lgb.Booster(model_file=str(ROOT / "artifacts/ai1/model.txt"))
        assert self.booster.feature_name() == FEATURES, "model feature order differs from the online feature list"
        cal = j("artifacts/ai1/calibrator.json")
        self.cx, self.cy = np.asarray(cal["x"], float), np.asarray(cal["y"], float)
        conf = j("artifacts/ai1/conformal.json")
        self.q0, self.q1 = conf["q0"], conf["q1"]
        nov = j("artifacts/ai1/novelty.json")
        self.nmed = np.array([nov["median"][f] for f in FEATURES])
        self.nscale = np.array([nov["scale"][f] for f in FEATURES])
        self.nthr = nov["threshold"]
        self.thr = j("artifacts/ai1/thresholds.json")
        self.rules = yaml.safe_load((ROOT / "configs/rules/actions.yaml").read_text(encoding="utf-8"))
        model_sha = next(r["sha256"] for r in self.verification["files"] if r["path"].endswith("model.txt"))
        commit = next(r["code_commit"] for r in self.verification["files"] if r["path"].endswith("model.txt")) or "unknown"
        self.version = f"ai1-lightgbm-{model_sha[:12]}"
        self.info = {"model": "ai1_pause_check", "version": self.version, "sha256": model_sha, "code_commit": commit,
                     "data_version": self.verification["data_version"], "trees": self.booster.num_trees()}
        from uvera_ml.policy import decide  # same policy as the monolith (configs/rules/actions.yaml)
        from uvera_ml.xai.reasons import safe_reasons, top_reasons
        self._decide, self._top, self._safe = decide, top_reasons, safe_reasons

    def score(self, x: np.ndarray, amount: float, explain: str = "auto") -> dict:
        X = x.reshape(1, -1)
        raw = float(self.booster.predict(X, num_threads=1)[0])
        p = float(np.interp(raw, self.cx, self.cy))
        in0, in1 = p <= self.q0, (1 - p) <= self.q1
        cstate = "confident_low" if in0 and not in1 else "confident_high" if in1 and not in0 else "unsure"
        z = np.nan_to_num(np.abs((x - self.nmed) / self.nscale), nan=0.0)
        ood = bool(np.sort(z)[-3:].mean() > self.nthr)
        d = self._decide(raw, cstate, ood, self.thr, amount, self.rules)
        reasons = []
        if explain == "always" or (explain == "auto" and d["state"] != "confident_low"):
            contrib = self.booster.predict(X, pred_contrib=True, num_threads=1)[0]
            values = dict(zip(FEATURES, x.tolist()))
            reasons = (self._safe if d["state"] == "confident_low" else self._top)(contrib, values, FEATURES)
        return {"model_version": self.version, "raw_score": raw, "p_calibrated": p, "conformal_state": cstate,
                "ood": ood, "risk_level": d["risk_level"], "unsure": d["uncertainty_state"] == "unsure",
                "state": d["state"], "recommendation": d["recommendation"], "human_review": d["human_review"],
                "reasons": reasons}

    def score_batch(self, X: np.ndarray, amounts: list[float], explain: str = "auto") -> list[dict]:
        """Vectorised scoring for micro-batches (stream/shadow path): one LightGBM call for all rows."""
        raw = self.booster.predict(X, num_threads=1)
        p = np.interp(raw, self.cx, self.cy)
        in0, in1 = p <= self.q0, (1 - p) <= self.q1
        z = np.nan_to_num(np.abs((X - self.nmed) / self.nscale), nan=0.0)
        ood = np.sort(z, axis=1)[:, -3:].mean(axis=1) > self.nthr
        out = []
        for i in range(len(X)):
            cstate = "confident_low" if in0[i] and not in1[i] else "confident_high" if in1[i] and not in0[i] else "unsure"
            d = self._decide(float(raw[i]), cstate, bool(ood[i]), self.thr, amounts[i], self.rules)
            out.append({"model_version": self.version, "raw_score": float(raw[i]), "p_calibrated": float(p[i]),
                        "conformal_state": cstate, "ood": bool(ood[i]), "risk_level": d["risk_level"],
                        "unsure": d["uncertainty_state"] == "unsure", "state": d["state"],
                        "recommendation": d["recommendation"], "human_review": d["human_review"], "reasons": []})
        idx = [i for i, r in enumerate(out) if explain == "always" or (explain == "auto" and r["state"] != "confident_low")]
        if idx:
            contrib = self.booster.predict(X[idx], pred_contrib=True, num_threads=1)
            for j, i in enumerate(idx):
                fn = self._safe if out[i]["state"] == "confident_low" else self._top
                out[i]["reasons"] = fn(contrib[j], dict(zip(FEATURES, X[i].tolist())), FEATURES)
        return out


class TextModel:
    """AI-2 Scam Text Check, TF-IDF + logistic regression (the CPU-cheap served variant), isotonic-calibrated."""

    def __init__(self):
        self.verification = verify(AI2_FILES)
        import joblib

        self.model = joblib.load(ROOT / "artifacts/ai2/tfidf_lr.joblib")
        info = json.loads((ROOT / "artifacts/ai2/model_info.json").read_text(encoding="utf-8"))
        self.classes = info["classes"]
        self.legit = self.classes.index("legit")
        cal = (info.get("verdict_calibrators") or {}).get("tfidf_lr")
        self.cx = np.asarray(cal["x"], float) if cal else None
        self.cy = np.asarray(cal["y"], float) if cal else None
        sha = self.verification["files"][0]["sha256"]
        self.version = f"ai2-tfidf-lr-{sha[:12]}"
        self.info = {"model": "ai2_text_check", "version": self.version, "sha256": sha}

    def check(self, text: str) -> dict:
        pr = self.model.predict_proba([text.strip()[:1000]])[0]
        raw = 1 - pr[self.legit]
        p = float(np.clip(np.interp(raw, self.cx, self.cy) if self.cx is not None else raw, 0.02, 0.98))
        order = np.argsort(-pr)
        fam = self.classes[int(order[0])] if order[0] != self.legit or p < 0.5 else self.classes[int(order[1])]
        state = "likely_scam" if p >= 0.7 else "likely_safe" if p <= 0.3 else "unsure"
        return {"model_version": self.version, "p_scam": p, "state": state,
                "family": fam if state != "likely_safe" else "legit",
                "top_families": [{"family": self.classes[int(i)], "probability": float(pr[i])} for i in order[:3]]}
