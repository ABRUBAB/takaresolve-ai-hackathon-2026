"""Postgres access for the scorer: decisions (sync or batched COPY), alerts, cases and the audit log."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import asyncpg

DECISION_COLS = ["id", "event_id", "source", "sender", "receiver", "amount", "channel", "sim_t", "p_calibrated",
                 "raw_score", "risk_level", "state", "unsure", "ood", "model_version", "latency_ms", "reasons",
                 "replica", "produced_at", "decided_at"]
ALERT_COLS = ["decision_id", "event_id", "wallet", "kind", "level", "status"]
INSERT_DECISION = (f"INSERT INTO decisions ({', '.join(DECISION_COLS)}) VALUES "
                   f"({', '.join(f'${i + 1}' for i in range(len(DECISION_COLS)))})")


def decision_row(body, result: dict, latency_ms: float, replica: str, source: str) -> tuple:
    produced = datetime.fromtimestamp(body.produced_ms / 1000, timezone.utc) if body.produced_ms else None
    reasons = json.dumps([{"f": r["feature"], "c": round(r["contribution"], 4)} for r in result["reasons"]])
    return (uuid.uuid4(), body.event_id, source, body.sender, body.receiver, Decimal(f"{body.amount:.2f}"), body.channel,
            body.t, result["p_calibrated"], result["raw_score"], result["risk_level"], result["state"], result["unsure"],
            result["ood"], result["model_version"], latency_ms, reasons, replica, produced, datetime.now(timezone.utc))


class DecisionWriter:
    """mode=sync: INSERT per request inside the request. mode=batch: queue + COPY every FLUSH_MS or MAX_ROWS."""

    def __init__(self, pool: asyncpg.Pool, mode: str = "batch", flush_ms: int = 50, max_rows: int = 1000):
        self.pool, self.mode, self.flush_s, self.max_rows = pool, mode, flush_ms / 1000, max_rows
        self.queue: list[tuple] = []
        self.task: asyncio.Task | None = None
        self.written = 0
        self.flush_seconds: list[float] = []

    def start(self) -> None:
        if self.mode == "batch":
            self.task = asyncio.create_task(self._loop())

    async def write(self, row: tuple) -> None:
        if self.mode == "off":
            return
        if self.mode == "sync":
            async with self.pool.acquire() as con:
                async with con.transaction():
                    await con.execute(INSERT_DECISION, *row)
                    if row[10] == "high":
                        await con.execute("INSERT INTO alerts (decision_id, event_id, wallet, kind, level) VALUES ($1,$2,$3,'pause_check','high')",
                                          row[0], row[1], row[4])
            self.written += 1
            return
        self.queue.append(row)

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.flush_s)
            await self.flush()

    async def flush(self) -> None:
        while self.queue:
            rows, self.queue = self.queue[: self.max_rows], self.queue[self.max_rows:]
            alerts = [(r[0], r[1], r[4], "pause_check", "high", "open") for r in rows if r[10] == "high"]
            t0 = time.perf_counter()
            try:
                async with self.pool.acquire() as con:
                    async with con.transaction():
                        await con.copy_records_to_table("decisions", records=rows, columns=DECISION_COLS)
                        if alerts:
                            await con.copy_records_to_table("alerts", records=alerts, columns=ALERT_COLS)
                self.written += len(rows)
            except Exception as e:  # noqa: BLE001 - never lose the request path; re-queue and retry next tick
                print("decision flush failed, will retry:", repr(e)[:200])
                self.queue = rows + self.queue
                return
            self.flush_seconds.append(time.perf_counter() - t0)
            self.flush_seconds = self.flush_seconds[-200:]


async def create_alert(pool: asyncpg.Pool, wallet: str, kind: str, level: str, event_id: int | None, actor: str) -> int:
    async with pool.acquire() as con:
        async with con.transaction():
            aid = await con.fetchval("INSERT INTO alerts (event_id, wallet, kind, level) VALUES ($1,$2,$3,$4) RETURNING id",
                                     event_id, wallet, kind, level)
            await con.execute("INSERT INTO audit_log (actor, action, entity, entity_id, detail) VALUES ($1,'alert.create','alert',$2,$3)",
                              actor, str(aid), json.dumps({"wallet": wallet, "kind": kind, "level": level}))
    return aid


async def link_case(pool: asyncpg.Pool, wallet: str, kind: str, actor: str) -> dict:
    """Agent/ops report on a wallet: new alert, linked to the open case of that wallet (or a new case), audited."""
    async with pool.acquire() as con:
        async with con.transaction():
            await con.execute("SELECT pg_advisory_xact_lock(hashtext($1))", wallet)  # one case per wallet, no races
            cid = await con.fetchval("SELECT c.id FROM case_wallets w JOIN cases c ON c.id = w.case_id "
                                     "WHERE w.wallet = $1 AND c.status = 'open' LIMIT 1", wallet)
            created = cid is None
            if created:
                cid = await con.fetchval("INSERT INTO cases (title, priority) VALUES ($1, 2) RETURNING id", f"Reports on {wallet}")
                await con.execute("INSERT INTO case_wallets (case_id, wallet, role) VALUES ($1,$2,'receiver')", cid, wallet)
            aid = await con.fetchval("INSERT INTO alerts (event_id, wallet, kind, level, case_id) VALUES (NULL,$1,$2,'medium',$3) RETURNING id",
                                     wallet, kind, cid)
            await con.execute("UPDATE cases SET updated_at = now(), n_alerts = n_alerts + 1 WHERE id = $1", cid)
            await con.execute("INSERT INTO audit_log (actor, action, entity, entity_id, detail) VALUES ($1,'case.link','case',$2,$3)",
                              actor, str(cid), json.dumps({"wallet": wallet, "alert_id": aid, "created": created}))
    return {"case_id": cid, "alert_id": aid, "case_created": created}


async def get_case(pool: asyncpg.Pool, case_id: int) -> dict | None:
    async with pool.acquire() as con:
        c = await con.fetchrow("SELECT id, status, title, priority, n_alerts, created_at, updated_at FROM cases WHERE id = $1", case_id)
        if c is None:
            return None
        alerts = await con.fetch("SELECT id, wallet, kind, level, status, created_at FROM alerts WHERE case_id = $1 "
                                 "ORDER BY created_at DESC LIMIT 50", case_id)
        wallets = await con.fetch("SELECT wallet, role FROM case_wallets WHERE case_id = $1", case_id)
    return {**{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(c).items()},
            "wallets": [dict(w) for w in wallets],
            "alerts": [{**dict(a), "created_at": a["created_at"].isoformat()} for a in alerts]}
