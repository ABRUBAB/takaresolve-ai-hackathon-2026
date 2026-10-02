"""SQLite storage for human decisions: case status, review actions and an append-only audit log."""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from app.core.config import settings

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS case_status (case_key TEXT PRIMARY KEY, status TEXT NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS review_action (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_key TEXT NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL,
  actor_role TEXT NOT NULL, actor_id TEXT NOT NULL, trace_id TEXT, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, actor TEXT, route TEXT, trace_id TEXT, summary TEXT);
"""


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn


def audit(actor: str, route: str, trace_id: str, summary: str) -> None:
    with _lock:
        conn().execute("INSERT INTO audit_log(at, actor, route, trace_id, summary) VALUES (?,?,?,?,?)",
                       (time.time(), actor, route, trace_id, summary[:500]))
        conn().commit()


def record_action(case_key: str, action: str, reason: str, role: str, actor: str, trace_id: str) -> dict:
    status = {"approve_hold": "hold_approved", "request_evidence": "evidence_requested", "escalate": "escalated",
              "dismiss": "closed_no_action", "close": "closed"}.get(action, "in_review")
    now = time.time()
    with _lock:
        c = conn()
        c.execute("INSERT INTO review_action(case_key, action, reason, actor_role, actor_id, trace_id, at) VALUES (?,?,?,?,?,?,?)",
                  (case_key, action, reason, role, actor, trace_id, now))
        c.execute("INSERT INTO case_status(case_key, status, updated_at) VALUES (?,?,?) "
                  "ON CONFLICT(case_key) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at", (case_key, status, now))
        c.commit()
    return {"case_key": case_key, "status": status, "at": now}


def statuses() -> dict:
    return {r["case_key"]: r["status"] for r in conn().execute("SELECT case_key, status FROM case_status")}


def actions(case_key: str) -> list[dict]:
    rows = conn().execute("SELECT action, reason, actor_role, actor_id, trace_id, at FROM review_action WHERE case_key=? ORDER BY at DESC",
                          (case_key,))
    return [dict(r) for r in rows]
