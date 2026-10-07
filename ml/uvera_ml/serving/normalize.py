"""Adversarial text normalisation for AI-2 (and the prompt-injection check).

Scammers disguise trigger words so that filters miss them: invisible characters inside words, look-alike letters from other
alphabets, "p.r.i.z.e" spacing, "pr1ze" digits, "priiiize" repeats. This undoes those tricks before the model sees the text.
Bengali characters are never changed (Unicode NFKC would decompose letters such as U+09DF and alter Bangla n-grams), so a
normal Bangla, Banglish or English message is returned unchanged.
"""
from __future__ import annotations

import re
import unicodedata

_INVISIBLE = dict.fromkeys(map(ord, "​⁠﻿­᠎‎‏‪‫‬‭‮"), None)
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h",
    "к": "k", "І": "I", "Ѕ": "S", "Ј": "J", "м": "m", "т": "t", "в": "b", "н": "h", "ɡ": "g", "ⅼ": "l", "Ι": "I", "Α": "A", "Β": "B", "Ε": "E", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Χ": "X", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "ο": "o", "α": "a", "ε": "e", "ι": "i", "ν": "v", "υ": "u",
})
_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"}
_SPLIT = re.compile(r"(?<![^\W\d_])((?:[A-Za-z][\.\-_\*·•]){2,}[A-Za-z])(?![^\W\d_])")  # p.r.i.z.e, p-r-i-z-e
_SPACED = re.compile(r"(?<!\S)((?:[A-Za-z] ){3,}[A-Za-z])(?!\S)")  # "p r i z e" (4+ single letters; "won a prize" untouched)
_REPEAT = re.compile(r"([a-wyz])\1{2,}")  # lowercase only and never x: masked numbers like 01XXXXXXXXX stay as they are
_LEET_WORD = re.compile(r"\b(?=[A-Za-z0-9@$!]*[A-Za-z])(?=[A-Za-z0-9@$!]*[0-9@$!])[A-Za-z0-9@$!]{3,}\b")


def _is_bengali(ch: str) -> bool:
    return "ঀ" <= ch <= "৿"


def _fold(ch: str) -> str:
    """Fold a styled/full-width character to plain ASCII letters or digits; leave everything else (emoji, Bengali) alone."""
    if ord(ch) < 128 or _is_bengali(ch):
        return ch
    n = unicodedata.normalize("NFKC", ch)
    return n if n.isascii() and n.isalnum() else ch


def _nfkc_non_bengali(text: str) -> str:
    return "".join(_fold(ch) for ch in text)


def _deleet(m: re.Match) -> str:
    """Only a digit/symbol sitting BETWEEN letters is a disguised letter ("pr1ze", "w1n"); amounts like "Tk3000", wallet ids
    like "C008170" and codes keep their digits."""
    w = list(m.group(0))
    for i, c in enumerate(w):
        if c in _LEET and 0 < i < len(w) - 1 and w[i - 1].isalpha() and (w[i + 1].isalpha() or w[i + 1] in _LEET and i + 2 < len(w) and w[i + 2].isalpha()):
            w[i] = _LEET[c]
    return "".join(w)


def _strip_zw(text: str) -> str:
    text = text.translate(_INVISIBLE)
    # ZWJ/ZWNJ are part of correct Bengali spelling; keep them only between Bengali characters
    out = []
    for i, ch in enumerate(text):
        if ch in "‌‍":
            prev, nxt = (text[i - 1] if i else ""), (text[i + 1] if i + 1 < len(text) else "")
            if not (_is_bengali(prev) and _is_bengali(nxt)):
                continue
        out.append(ch)
    return "".join(out)


def normalize_text(text: str) -> str:
    if not text:
        return text
    t = _strip_zw(text)
    t = _nfkc_non_bengali(t)
    t = t.translate(_HOMOGLYPHS)
    t = _SPLIT.sub(lambda m: re.sub(r"[\.\-_\*·•]", "", m.group(1)), t)
    t = _SPACED.sub(lambda m: m.group(1).replace(" ", ""), t)
    t = _LEET_WORD.sub(_deleet, t)
    t = _REPEAT.sub(r"\1\1", t)
    return t
