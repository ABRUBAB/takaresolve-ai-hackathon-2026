"""AI-7 live briefs: cache -> Gemini (if enabled) -> validator -> template. Never blocks a response."""
from __future__ import annotations

import hashlib
import json
import os

from uvera_ml.brief import grounding as G
from uvera_ml.serving.store import ArtifactStore


def _key(ev: dict) -> str:
    return hashlib.sha256(json.dumps(ev, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


class BriefEngine:
    def __init__(self, store: ArtifactStore, mode: str | None = None):
        self.mode = (mode or os.environ.get("LLM_MODE", "cached")).lower()
        self.retriever = G.CardRetriever(G.load_cards())
        cache = store.json("artifacts/ai7/briefs_cache.json", {}) or {}
        self.cache = {k: v["brief"] for k, v in cache.items()}
        self.gemini = None
        if self.mode == "live":
            try:
                from uvera_ml.brief.gemini import Gemini

                self.gemini = Gemini(min_interval_s=1.0, max_retries=2, timeout_s=8)
            except Exception as e:  # noqa: BLE001 - no key / no SDK: templates are used
                print("Gemini disabled:", str(e)[:120])
        self.stats = {"cache": 0, "gemini": 0, "template": 0, "validator_rejections": 0}

    def _render(self, ev: dict) -> dict:
        k = _key(ev)
        if k in self.cache:
            self.stats["cache"] += 1
            return {**self.cache[k], "source": self.cache[k].get("source", "gemini") + "_cached"}
        if self.gemini is not None:
            try:
                out = self.gemini.json(G.prompt_for(ev), G.Brief, temperature=0.3, system=G.SYSTEM)
                ok, problems = G.validate(out, ev)
                if ok:
                    out = {**out, "source": "gemini"}
                    self.cache[k] = out
                    self.stats["gemini"] += 1
                    return out
                self.stats["validator_rejections"] += 1
            except Exception:  # noqa: BLE001 - fall through to the template
                pass
        self.stats["template"] += 1
        return G.template_brief(ev)

    def for_transfer(self, check: dict, amount: float, note: str | None = None) -> dict:
        reasons = check["reasons"]
        cards = self.retriever.retrieve(" ".join(r["text_en"] for r in reasons) or "transfer", [])
        row = {"reasons": reasons, "p_calibrated": check["calibrated_probability"], "amount": amount}
        ev = G.transfer_evidence(row, check, cards, note)
        return {**self._render(ev), "evidence_object": ev}

    def for_case(self, case: dict) -> dict:
        tags = ["qr_misuse"] if case["merchants"] else ["mule_signals"]
        cards = self.retriever.retrieve(" ".join(e["text"] for e in case["evidence"]), tags)
        ev = G.case_evidence(case, cards)
        return {**self._render(ev), "evidence_object": ev}
