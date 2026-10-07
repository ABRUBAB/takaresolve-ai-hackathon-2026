"""SQLite storage for human decisions: case status, review actions and an append-only, hash-chained audit log.

Tamper evidence: every audit row stores prev_hash and hash = sha256(prev_hash + canonical JSON of the row), and SQLite
triggers abort any UPDATE or DELETE on audit_log and review_action. verify_audit() recomputes the chain and reports the
first broken row. (Production adds WORM storage and an external anchor for the head hash: docs/security.md.)
"""
from __future__ import annotations

import hashlib
import json
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
  id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, actor TEXT, route TEXT, trace_id TEXT, summary TEXT,
  prev_hash TEXT, hash TEXT);
"""
GENESIS = "0" * 64
APPEND_ONLY_TABLES = ("audit_log", "review_action")
APPEND_ONLY = "".join(
    f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END; "
    for t in APPEND_ONLY_TABLES for op in ("UPDATE", "DELETE"))
AUDIT_FIELDS = ("at", "actor", "route", "trace_id", "summary")


def chain_hash(prev_hash: str, row: dict) -> str:
    """sha256(prev_hash + canonical JSON of the row's fields)."""
    canonical = json.dumps({k: row[k] for k in AUDIT_FIELDS}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def _migrate(c: sqlite3.Connection) -> None:
    """Older databases: add the hash columns and chain the existing rows once, before the append-only triggers exist."""
    cols = {r[1] for r in c.execute("PRAGMA table_info(audit_log)")}
    if "hash" not in cols:
        c.execute("ALTER TABLE audit_log ADD COLUMN prev_hash TEXT")
        c.execute("ALTER TABLE audit_log ADD COLUMN hash TEXT")
    triggers = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    if "audit_log_no_update" not in triggers:
        prev = GENESIS
        for r in c.execute("SELECT id, at, actor, route, trace_id, summary, hash FROM audit_log ORDER BY id").fetchall():
            if r["hash"] is None:
                h = chain_hash(prev, dict(r))
                c.execute("UPDATE audit_log SET prev_hash=?, hash=? WHERE id=?", (prev, h, r["id"]))
                prev = h
            else:
                prev = r["hash"]
    c.executescript(APPEND_ONLY)
    c.commit()


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        _migrate(_conn)
    return _conn


def audit(actor: str, route: str, trace_id: str, summary: str) -> None:
    """Append one audit row, chained to the previous one. BEGIN IMMEDIATE takes SQLite's write lock before the chain
    head is read, so two API processes sharing the file cannot fork the chain."""
    row = {"at": time.time(), "actor": actor, "route": route, "trace_id": trace_id, "summary": summary[:500]}
    with _lock:
        c = conn()
        if not c.in_transaction:
            c.execute("BEGIN IMMEDIATE")
        try:
            last = c.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
            prev = last["hash"] if last and last["hash"] else GENESIS
            c.execute("INSERT INTO audit_log(at, actor, route, trace_id, summary, prev_hash, hash) VALUES (?,?,?,?,?,?,?)",
                      (row["at"], actor, route, trace_id, row["summary"], prev, chain_hash(prev, row)))
            c.commit()
        except Exception:
            c.rollback()
            raise


def verify_audit() -> dict:
    """Recompute the hash chain. first_broken_index is the 0-based position of the first row whose stored hashes do not
    match (a changed, deleted or inserted row), else None. head_hash can be anchored outside the database."""
    c = conn()
    rows = c.execute("SELECT id, at, actor, route, trace_id, summary, prev_hash, hash FROM audit_log ORDER BY id").fetchall()
    triggers = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    out = {"ok": True, "rows": len(rows), "first_broken_index": None, "first_broken_id": None, "head_hash": GENESIS,
           "append_only_triggers": all(f"{t}_no_{op}" in triggers for t in APPEND_ONLY_TABLES for op in ("update", "delete"))}
    prev = GENESIS
    for i, r in enumerate(rows):
        if r["prev_hash"] != prev or r["hash"] != chain_hash(prev, dict(r)):
            out.update(ok=False, first_broken_index=i, first_broken_id=r["id"])
            break
        prev = r["hash"]
    out["head_hash"] = prev if out["ok"] else None
    return out


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
