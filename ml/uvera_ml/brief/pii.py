"""PII scrubbing before any text leaves the API for the LLM (AI-7 live mode).

Replaces, in English, Bangla and Banglish text (ASCII or Bangla digits ০-৯):
  emails -> [EMAIL], links and bare web addresses -> [URL], card-like 16-digit numbers -> [CARD],
  Bangladesh mobile numbers (+8801XXXXXXXXX, 8801..., 01XXXXXXXXX, with spaces or dashes) -> [PHONE],
  10/13/17-digit national-ID-like numbers -> [NID], one-time codes / PINs next to the words OTP, PIN, code -> [OTP].
Amounts such as "Tk 5,000" and ids such as R1 or PC-03 are kept, so the evidence still reads correctly.
The scrubber is deliberately greedy: a false positive only hides a number from the LLM, a miss would leak it.
"""
from __future__ import annotations

import re
from typing import Any

BN_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
SEP = r"[\s\-.]?"
_NOT_DIGIT_BEFORE = r"(?<![0-9])"
_NOT_DIGIT_AFTER = r"(?![0-9])"

# order matters: emails before links, cards before phones, phones (incl. 880 prefix = 13 digits) before NIDs
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")),
    ("URL", re.compile(r"(?:https?://|www\.)[^\s\"'<>]+", re.I)),
    ("URL", re.compile(r"\b[a-z0-9][a-z0-9\-]*(?:\.[a-z0-9\-]+)*\.(?:com|net|org|info|biz|xyz|top|club|site|online|link|"
                       r"click|live|shop|app|io|me|co|ly|gl|bd|in)(?:/[^\s\"'<>]*)?\b", re.I)),
    ("CARD", re.compile(_NOT_DIGIT_BEFORE + r"[0-9]{4}(?:[\s\-]?[0-9]{4}){3}" + _NOT_DIGIT_AFTER)),
    ("PHONE", re.compile(_NOT_DIGIT_BEFORE + r"(?:\+?880" + SEP + r"|0)1[3-9][0-9]{2}" + SEP + r"[0-9]{3}" + SEP + r"[0-9]{3}"
                         + _NOT_DIGIT_AFTER)),
    ("NID", re.compile(_NOT_DIGIT_BEFORE + r"(?:[0-9]{17}|[0-9]{13}|[0-9]{10})" + _NOT_DIGIT_AFTER)),
    ("OTP", re.compile(r"(?i)(?:\b(?:otp|pin|code|passcode|verification code)\b|ওটিপি|পিন|কোড)\D{0,12}?"
                       + _NOT_DIGIT_BEFORE + r"([0-9]{4,8})" + _NOT_DIGIT_AFTER)),
]


def scrub(text: str) -> tuple[str, dict[str, int]]:
    """Return (scrubbed text, {kind: count}). Bangla digits are matched too (the replacement keeps the rest intact)."""
    if not text:
        return text, {}
    counts: dict[str, int] = {}
    for kind, pat in PATTERNS:
        # match on an ASCII-digit copy (same length: one character for one character), replace in the real text
        ascii_view = text.translate(BN_TO_ASCII)
        spans = []
        for m in pat.finditer(ascii_view):
            start, end = (m.start(1), m.end(1)) if kind == "OTP" else (m.start(), m.end())
            spans.append((start, end))
        for start, end in reversed(spans):
            text = text[:start] + f"[{kind}]" + text[end:]
        if spans:
            counts[kind] = counts.get(kind, 0) + len(spans)
    return text, counts


def scrub_obj(obj: Any, counts: dict[str, int] | None = None) -> tuple[Any, dict[str, int]]:
    """Scrub every string inside a JSON-like object (dicts, lists); keys and non-strings are kept."""
    counts = {} if counts is None else counts
    if isinstance(obj, str):
        out, c = scrub(obj)
        for k, v in c.items():
            counts[k] = counts.get(k, 0) + v
        return out, counts
    if isinstance(obj, dict):
        return {k: scrub_obj(v, counts)[0] for k, v in obj.items()}, counts
    if isinstance(obj, list | tuple):
        return [scrub_obj(v, counts)[0] for v in obj], counts
    return obj, counts
