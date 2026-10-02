"""Phrase occlusion for text: remove a window of words and measure how much the scam probability drops.

This is faithful by construction: a phrase is only highlighted if removing it really changes the model output.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np


def occlusion(text: str, predict_scam: Callable[[list[str]], np.ndarray], window: int = 3, top_k: int = 3) -> list[dict]:
    words = text.split()
    if not words:
        return []
    base = float(predict_scam([text])[0])
    spans = [(i, min(len(words), i + window)) for i in range(0, len(words), max(1, window // 2 + 1))]
    variants = [" ".join(words[:a] + words[b:]) or "." for a, b in spans]
    scores = predict_scam(variants)
    drops = base - np.asarray(scores, float)
    order = np.argsort(-drops)[:top_k]
    return [{"phrase": " ".join(words[spans[i][0]:spans[i][1]]), "drop": round(float(drops[i]), 4), "start_word": spans[i][0]}
            for i in order if drops[i] > 0.01]
