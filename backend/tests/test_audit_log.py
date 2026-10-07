"""Tamper-evident audit log: append-only triggers, hash chain, verification endpoint, migration of older databases."""
import sqlite3

import pytest
from app import db
from app.core.config import settings
from app.core.security import issue
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    path = tmp_path / "audit.db"
    monkeypatch.setattr(settings, "db_path", str(path))
    monkeypatch.setattr(db, "_conn", None)
    yield path
    if db._conn is not None:
        db._conn.close()


def write_rows(n: int) -> None:
    for i in range(n):
        db.audit(f"OPS-{i}", f"/cases/CASE-{i:04d}/actions", f"trace{i}", f"request_evidence: reason number {i}")


def bypass(path, sql: str, *params) -> None:
    """What an attacker with file access could do: drop the protecting trigger, then edit the table directly."""
    c = sqlite3.connect(path)
    c.execute("DROP TRIGGER IF EXISTS audit_log_no_update")
    c.execute("DROP TRIGGER IF EXISTS audit_log_no_delete")
    c.execute(sql, params)
    c.commit()
    c.close()


def test_chain_verifies_after_appends(fresh_db):
    write_rows(5)
    out = db.verify_audit()
    assert out["ok"] and out["rows"] == 5 and out["first_broken_index"] is None
    assert out["append_only_triggers"] is True and len(out["head_hash"]) == 64
    rows = db.conn().execute("SELECT prev_hash, hash FROM audit_log ORDER BY id").fetchall()
    assert rows[0]["prev_hash"] == db.GENESIS
    assert all(rows[i]["prev_hash"] == rows[i - 1]["hash"] for i in range(1, 5))


def test_empty_log_verifies(fresh_db):
    assert db.verify_audit() == {"ok": True, "rows": 0, "first_broken_index": None, "first_broken_id": None,
                                 "head_hash": db.GENESIS, "append_only_triggers": True}


@pytest.mark.parametrize("sql", ["UPDATE audit_log SET summary='approve_hold: changed' WHERE id=2",
                                 "DELETE FROM audit_log WHERE id=2",
                                 "UPDATE review_action SET reason='changed'", "DELETE FROM review_action"])
def test_update_and_delete_are_refused_by_triggers(fresh_db, sql):
    write_rows(3)
    db.record_action("CASE-0001", "note", "a reviewer note for the test", "ops", "OPS-1", "t1")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        db.conn().execute(sql)
    db.conn().rollback()
    assert db.verify_audit()["ok"]


def test_edited_row_is_detected(fresh_db):
    write_rows(5)
    bypass(fresh_db, "UPDATE audit_log SET summary='dismiss: nothing to see' WHERE id=3")
    out = db.verify_audit()
    assert out["ok"] is False and out["first_broken_index"] == 2 and out["first_broken_id"] == 3
    assert out["append_only_triggers"] is False and out["head_hash"] is None


def test_deleted_row_is_detected(fresh_db):
    write_rows(5)
    bypass(fresh_db, "DELETE FROM audit_log WHERE id=2")
    out = db.verify_audit()
    assert out["ok"] is False and out["first_broken_index"] == 1 and out["first_broken_id"] == 3


def test_recomputed_hash_without_relinking_is_detected(fresh_db):
    """Even an attacker who recomputes the edited row's own hash breaks the link to the next row."""
    write_rows(4)
    c = db.conn()
    r = dict(c.execute("SELECT * FROM audit_log WHERE id=2").fetchone())
    r["summary"] = "escalate: forged"
    bypass(fresh_db, "UPDATE audit_log SET summary=?, hash=? WHERE id=2", r["summary"], db.chain_hash(r["prev_hash"], r))
    out = db.verify_audit()
    assert out["ok"] is False and out["first_broken_index"] == 2  # row 3's prev_hash no longer matches


def test_triggers_come_back_on_restart(fresh_db, monkeypatch):
    write_rows(2)
    bypass(fresh_db, "SELECT 1")  # drops both triggers
    db._conn.close()
    monkeypatch.setattr(db, "_conn", None)
    assert db.verify_audit()["append_only_triggers"] is True


def test_old_database_is_migrated_and_chained(fresh_db):
    c = sqlite3.connect(fresh_db)
    c.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, actor TEXT, route TEXT, "
              "trace_id TEXT, summary TEXT)")
    for i in range(3):
        c.execute("INSERT INTO audit_log(at, actor, route, trace_id, summary) VALUES (?,?,?,?,?)",
                  (1700000000.5 + i, "OPS-1", "/cases/X/actions", f"t{i}", f"note: legacy row {i}"))
    c.commit()
    c.close()
    write_rows(2)  # opens through db.conn(): migration, then two chained rows
    out = db.verify_audit()
    assert out["ok"] and out["rows"] == 5 and out["append_only_triggers"]


def test_verify_endpoint_roles(fresh_db):
    write_rows(3)
    assert client.get("/v1/ops/audit/verify").status_code == 401
    cust = {"Authorization": f"Bearer {issue('customer', 'C000001')}"}
    assert client.get("/v1/ops/audit/verify", headers=cust).status_code == 403
    ops = {"Authorization": f"Bearer {issue('ops', 'OPS-1')}"}
    r = client.get("/v1/ops/audit/verify", headers=ops)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["rows"] == 3 and body["first_broken_index"] is None
    bypass(fresh_db, "UPDATE audit_log SET actor='someone-else' WHERE id=1")
    body = client.get("/v1/ops/audit/verify", headers=ops).json()
    assert body["ok"] is False and body["first_broken_index"] == 0
