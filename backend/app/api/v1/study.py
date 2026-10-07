"""On-site user study: anonymous responses from the /study page, plus aggregate results for the team.

Participants submit without signing in. Nothing personal is stored: no names, no phone numbers, no device data.
Results and the CSV export need the ops role or the study PIN (STUDY_RESULTS_PIN, sent as the X-Study-Pin header).
"""
from __future__ import annotations

import csv
import hmac
import io
import json
import re
import secrets
import statistics
import time
from collections import Counter, defaultdict, deque
from math import sqrt
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app import db
from app.core.config import settings
from app.core.security import current
from app.core.telemetry import client_key

router = APIRouter(tags=["study"])

MAX_BYTES = 20_000
SUBMITS_PER_MINUTE = 30  # per client; every phone at a venue can share one public address
WRONG_PINS_PER_10_MIN = 10

SCHEMA = """
CREATE TABLE IF NOT EXISTS study_responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT, participant_id TEXT NOT NULL UNIQUE, client_id TEXT UNIQUE,
  study_version TEXT NOT NULL, received_at REAL NOT NULL, payload TEXT NOT NULL);
"""
_ready = False
_submits: dict[str, deque] = defaultdict(lambda: deque(maxlen=SUBMITS_PER_MINUTE + 1))
_wrong_pins: dict[str, deque] = defaultdict(lambda: deque(maxlen=WRONG_PINS_PER_10_MIN + 1))


def _table():
    global _ready
    c = db.conn()
    if not _ready:
        c.executescript(SCHEMA)
        _ready = True
    return c


# ---------------------------------------------------------------- payload

Scale = Field(default=None, ge=1, le=5)
Millis = Field(default=None, ge=0, le=3_600_000)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown keys (name, phone, ...) are rejected, never stored


class Profile(Strict):
    age_band: Literal["18-24", "25-34", "35-44", "45+"] | None = None
    mm_use: Literal["daily", "weekly", "rarely", "never"] | None = None
    phone_lang: Literal["bn", "en", "both"] | None = None
    scam_contact: Literal["yes", "no", "not_sure"] | None = None
    scam_loss: Literal["yes", "no", "prefer_not"] | None = None


class Task1(Strict):
    """The Pause screen (prize-scam transfer)."""
    lang: Literal["bn", "en"]
    q1_meaning: Literal["paused_scam", "failed", "blocked", "not_sure"] | None = None
    q2_action: Literal["wait", "verify", "ask", "send_anyway"] | None = None
    q3_reason: Literal["senders", "moves_on", "wallet_age", "none"] | None = None
    q4_clarity: int | None = Scale
    q5_trust: int | None = Scale
    q6_annoyance: int | None = Scale
    view_ms: int | None = Millis
    total_ms: int | None = Millis


class Task2(Strict):
    """The "Not sure, a person will check" screen."""
    lang: Literal["bn", "en"]
    q_next: Literal["person_checks", "sent", "lost", "not_sure"] | None = None
    q_ok_unsure: int | None = Scale
    view_ms: int | None = Millis
    total_ms: int | None = Millis


class Task3(Strict):
    """Analyst triage: version A = plain alert list, version B = alerts already linked into cases."""
    arm: Literal["A", "B"]
    rings: int | None = Field(default=None, ge=0, le=12)
    first_wallet: Literal["W-77", "W-31", "W-58", "R-104", "not_sure"] | None = None
    time_ms: int | None = Millis
    confidence: int | None = Scale


class StudyIn(Strict):
    study_version: str = Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")
    client_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$", description="Random id made by the page, so a retried upload is stored once")
    consent: Literal[True]
    facilitator: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{0,8}$")
    ui_lang: Literal["bn", "en"]
    assignment: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{0,24}$")
    started_at: str | None = Field(default=None, max_length=40)
    total_ms: int | None = Millis
    profile: Profile = Profile()
    task1: Task1 | None = None
    task2: Task2 | None = None
    task3: Task3 | None = None
    comment: str | None = Field(default=None, max_length=600)


PHONE = re.compile(r"(?:\+?\s*8\s*8\s*)?0\s*1[\d\s-]{8,12}\d|\b\d[\d\s-]{6,}\d\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _scrub(text: str | None) -> str | None:
    """Free text is optional; phone numbers, e-mail addresses and long digit runs are removed before storing."""
    if not text:
        return None
    text = EMAIL.sub("[removed]", text)
    text = PHONE.sub("[removed]", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text).strip()
    return text[:500] or None


def _throttle(table: dict[str, deque], key: str, limit: int, window: float) -> bool:
    now = time.time()
    q = table[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


@router.post("/study/responses", status_code=201)
async def submit(request: Request) -> dict:
    if int(request.headers.get("content-length") or 0) > MAX_BYTES:
        raise HTTPException(413, "Response too large")
    raw = await request.body()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Response too large")
    if not _throttle(_submits, client_key(request), SUBMITS_PER_MINUTE, 60):
        raise HTTPException(429, "Too many responses from this address, try again in a minute")
    try:
        body = StudyIn.model_validate_json(raw)
    except ValidationError as e:
        raise HTTPException(422, [{"loc": err["loc"], "msg": err["msg"]} for err in e.errors()[:10]]) from e
    body.comment = _scrub(body.comment)
    payload = body.model_dump(exclude={"client_id"})
    c = _table()
    with db._lock:
        hit = c.execute("SELECT participant_id FROM study_responses WHERE client_id=?", (body.client_id,)).fetchone()
        if hit:
            return {"participant_id": hit["participant_id"], "stored": False, "duplicate": True}
        pid = "P-" + secrets.token_hex(4).upper()
        c.execute("INSERT INTO study_responses(participant_id, client_id, study_version, received_at, payload) VALUES (?,?,?,?,?)",
                  (pid, body.client_id, body.study_version, time.time(), json.dumps(payload, ensure_ascii=False)))
        c.commit()
    return {"participant_id": pid, "stored": True, "duplicate": False}


# ---------------------------------------------------------------- results (team only)

def _authorize(request: Request) -> None:
    pin = request.headers.get("x-study-pin")
    if pin is not None:
        key = client_key(request)
        recent = _wrong_pins[key]
        while recent and time.time() - recent[0] > 600:
            recent.popleft()
        if len(recent) >= WRONG_PINS_PER_10_MIN:
            raise HTTPException(429, "Too many wrong PINs, try again in 10 minutes")
        if hmac.compare_digest(pin.encode(), (settings.study_results_pin or "uvera2026").encode()):
            return
        recent.append(time.time())
        raise HTTPException(401, "Wrong study PIN")
    if request.headers.get("authorization"):
        if current(request).get("role") == "ops":
            return
        raise HTTPException(403, "This needs the ops role or the study PIN")
    raise HTTPException(401, "Enter the study PIN or sign in with the ops role")


def _rows(version: str | None) -> list[dict]:
    q = "SELECT participant_id, study_version, received_at, payload FROM study_responses"
    args: tuple = ()
    if version:
        q += " WHERE study_version=?"
        args = (version,)
    out = []
    for r in _table().execute(q + " ORDER BY received_at", args):
        p = json.loads(r["payload"])
        p.pop("client_id", None)
        out.append({"participant_id": r["participant_id"], "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r["received_at"])),
                    **p, "study_version": r["study_version"]})
    return out


def _wilson(k: int, n: int) -> list[float] | None:
    if not n:
        return None
    z, p = 1.96, k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def _rate(values: list[bool]) -> dict:
    n, k = len(values), sum(values)
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None, "ci95": _wilson(k, n)}


def _mean(values: list[int | float]) -> dict:
    return {"n": len(values), "mean": round(statistics.fmean(values), 2) if values else None,
            "sd": round(statistics.stdev(values), 2) if len(values) > 1 else None}


def _median_s(values: list[int]) -> float | None:
    return round(statistics.median(values) / 1000, 1) if values else None


def _get(row: dict, task: str, key: str):
    return (row.get(task) or {}).get(key)


def aggregate(rows: list[dict]) -> dict:
    profile = {k: dict(Counter((r.get("profile") or {}).get(k) or "no_answer" for r in rows))
               for k in ("age_band", "mm_use", "phone_lang", "scam_contact", "scam_loss")}

    t1 = [r["task1"] for r in rows if r.get("task1")]
    t1_by_lang = {lang: [t for t in t1 if t.get("lang") == lang] for lang in ("bn", "en")}

    def comprehension(ts):
        return _rate([t["q1_meaning"] == "paused_scam" for t in ts if t.get("q1_meaning")])

    def stop(ts):
        return _rate([t["q2_action"] != "send_anyway" for t in ts if t.get("q2_action")])

    task1 = {
        "n": len(t1),
        "comprehension": {**comprehension(t1), "by_lang": {k: comprehension(v) for k, v in t1_by_lang.items()}},
        "stated_stop": {**stop(t1), "by_lang": {k: stop(v) for k, v in t1_by_lang.items()}},
        "meaning": dict(Counter(t["q1_meaning"] for t in t1 if t.get("q1_meaning"))),
        "actions": dict(Counter(t["q2_action"] for t in t1 if t.get("q2_action"))),
        "reasons": dict(Counter(t["q3_reason"] for t in t1 if t.get("q3_reason"))),
        "clarity": _mean([t["q4_clarity"] for t in t1 if t.get("q4_clarity")]),
        "trust": _mean([t["q5_trust"] for t in t1 if t.get("q5_trust")]),
        "annoyance": _mean([t["q6_annoyance"] for t in t1 if t.get("q6_annoyance")]),
        "median_view_s": _median_s([t["view_ms"] for t in t1 if t.get("view_ms") is not None]),
    }

    t2 = [r["task2"] for r in rows if r.get("task2")]
    task2 = {
        "n": len(t2),
        "understood": _rate([t["q_next"] == "person_checks" for t in t2 if t.get("q_next")]),
        "answers": dict(Counter(t["q_next"] for t in t2 if t.get("q_next"))),
        "ok_unsure": _mean([t["q_ok_unsure"] for t in t2 if t.get("q_ok_unsure")]),
    }

    task3 = {}
    for arm in ("A", "B"):
        ts = [r["task3"] for r in rows if (r.get("task3") or {}).get("arm") == arm]
        rings = [t["rings"] == 3 for t in ts if t.get("rings") is not None]
        wallet = [t["first_wallet"] == "W-77" for t in ts if t.get("first_wallet")]
        both = [t.get("rings") == 3 and t.get("first_wallet") == "W-77" for t in ts if t.get("rings") is not None and t.get("first_wallet")]
        times = [t["time_ms"] for t in ts if t.get("time_ms") is not None]
        task3[arm] = {"n": len(ts), "rings_correct": _rate(rings), "wallet_correct": _rate(wallet), "both_correct": _rate(both),
                      "median_time_s": _median_s(times), "times_s": [round(x / 1000, 1) for x in times],
                      "wallets": dict(Counter(t["first_wallet"] for t in ts if t.get("first_wallet"))),
                      "rings_answers": dict(Counter(str(t["rings"]) for t in ts if t.get("rings") is not None)),
                      "confidence": _mean([t["confidence"] for t in ts if t.get("confidence")])}

    return {
        "n": len(rows),
        "first_at": rows[0]["received_at"] if rows else None,
        "last_at": rows[-1]["received_at"] if rows else None,
        "versions": dict(Counter(r["study_version"] for r in rows)),
        "facilitators": dict(Counter(r.get("facilitator") or "none" for r in rows)),
        "profile": profile,
        "task1": task1,
        "task2": task2,
        "task3": task3,
        "comments": [r["comment"] for r in rows if r.get("comment")][-50:],
        "correct_answers": {"task1_q1": "paused_scam", "task2": "person_checks", "task3_rings": 3, "task3_wallet": "W-77"},
        "caveat": "Small n. A quick on-site usability study with volunteers, not a representative survey. Stated intentions, not observed behaviour.",
    }


@router.get("/study/results")
def results(request: Request, version: str | None = None) -> dict:
    _authorize(request)
    rows = _rows(version)
    return {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "synthetic_screens": True,
            "summary": aggregate(rows), "rows": rows}


def _flat(value: dict, out: dict, prefix: str = "") -> dict:
    for k, v in value.items():
        if isinstance(v, dict):
            _flat(v, out, f"{prefix}{k}.")
        else:
            out[f"{prefix}{k}"] = v
    return out


def _cell(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # no spreadsheet formulas from free text


@router.get("/study/export.csv")
def export_csv(request: Request, version: str | None = None) -> Response:
    _authorize(request)
    flat = [_flat(r, {}) for r in _rows(version)]
    cols: list[str] = []
    for r in flat:
        cols += [k for k in r if k not in cols]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in flat:
        w.writerow([_cell(r.get(c)) for c in cols])
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="uvera_study_responses.csv"', "Cache-Control": "no-store"})
