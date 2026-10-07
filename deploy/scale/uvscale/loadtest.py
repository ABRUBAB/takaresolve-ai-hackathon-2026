"""Closed-loop HTTP load generator (asyncio + httpx, several processes so the client is not the bottleneck).

Scenarios
  transfer   POST /score/transfer with real test-window p2p transfers (features read from the online store)
  mixed      70% transfer, 20% text check, 5% alert create, 3% case link, 2% case read (Postgres writes)
  text       POST /score/text
  monolith   POST /v1/pause-check on the existing FastAPI monolith (needs --token)

python -m uvscale.loadtest --url http://nginx:8080 --scenario transfer -c 32 -d 30 --out /repo/reports/scalability/x.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing as mp
import os
import random
import time

import numpy as np

DATA = os.environ.get("LOADGEN_DATA", "/repo/_outputs/scale")
MIX = [("transfer", 0.70), ("text", 0.20), ("alert", 0.05), ("case_link", 0.03), ("case_get", 0.02)]


def pick(rng: random.Random) -> str:
    x, acc = rng.random(), 0.0
    for name, w in MIX:
        acc += w
        if x < acc:
            return name
    return MIX[0][0]


async def _run(url: str, scenario: str, conc: int, duration: float, warmup: float, seed: int, token: str | None,
               explain: str | None, source: str) -> dict:
    import httpx

    data = json.load(open(f"{DATA}/loadgen.json", encoding="utf-8"))
    rows, texts = [tuple(x) for x in data["transfers"]], data["texts"]
    receivers = [x[1] for x in rows]
    rng = random.Random(seed)
    headers = {"authorization": f"Bearer {token}"} if token else {}
    limits = httpx.Limits(max_connections=conc, max_keepalive_connections=conc)
    rec: dict[str, list] = {}
    errors: dict[str, int] = {}
    case_ids: list[int] = []
    t_start = time.perf_counter()
    t_measure, t_end = t_start + warmup, t_start + warmup + duration

    def req_for(kind: str):
        if kind == "transfer":
            s, d, a, t, ch = rows[rng.randrange(len(rows))]
            body = {"sender": s, "receiver": d, "amount": a, "t": t, "channel": ch, "source": "loadtest"}
            if explain:
                body["explain"] = explain
            return "POST", "/score/transfer", body
        if kind == "monolith":
            s, d, a, t, ch = rows[rng.randrange(len(rows))]
            return "POST", "/v1/pause-check", {"sender_id": s, "recipient_wallet": d, "amount": a,
                                               "hour": round((t % 86400) / 3600, 2), "channel": ch}
        if kind == "text":
            return "POST", "/score/text", {"text": texts[rng.randrange(len(texts))][:1000]}
        if kind == "alert":
            return "POST", "/alerts", {"wallet": receivers[rng.randrange(len(receivers))], "kind": "agent_report"}
        if kind == "case_link":
            return "POST", "/cases/link", {"wallet": receivers[rng.randrange(200)], "kind": "agent_report"}
        if kind == "case_get":
            cid = case_ids[rng.randrange(len(case_ids))] if case_ids else 1
            return "GET", f"/cases/{cid}", None
        raise ValueError(kind)

    async def user(client):
        while True:
            now = time.perf_counter()
            if now >= t_end:
                return
            kind = pick(rng) if scenario == "mixed" else scenario
            if kind == "case_get" and not case_ids:
                kind = "case_link"
            method, path, body = req_for(kind)
            t0 = time.perf_counter()
            try:
                r = await client.request(method, path, json=body)
                ok = r.status_code < 400 or (kind == "case_get" and r.status_code == 404)
                if kind == "case_link" and r.status_code == 200 and len(case_ids) < 500:
                    case_ids.append(r.json()["case_id"])
            except Exception:  # noqa: BLE001
                ok = False
            t1 = time.perf_counter()
            if t0 >= t_measure:
                rec.setdefault(kind, []).append((t1 - t0) * 1000 if ok else -1.0)
                if not ok:
                    errors[kind] = errors.get(kind, 0) + 1

    async with httpx.AsyncClient(base_url=url, timeout=30, limits=limits, headers=headers) as client:
        await asyncio.gather(*[user(client) for _ in range(conc)])
    return {"latencies": {k: v for k, v in rec.items()}, "errors": errors}


def _proc(args, q):
    q.put(asyncio.run(_run(*args)))


def summarize(lat: list[float], duration: float) -> dict:
    a = np.asarray(lat, float)
    ok = a[a >= 0]
    if not len(ok):
        return {"n": int(len(a)), "errors": int(len(a)), "rps": 0}
    return {"n": int(len(a)), "errors": int((a < 0).sum()), "error_rate": round(float((a < 0).mean()), 5),
            "rps": round(len(ok) / duration, 1),
            "latency_ms": {"p50": round(float(np.percentile(ok, 50)), 2), "p90": round(float(np.percentile(ok, 90)), 2),
                           "p95": round(float(np.percentile(ok, 95)), 2), "p99": round(float(np.percentile(ok, 99)), 2),
                           "max": round(float(ok.max()), 2), "mean": round(float(ok.mean()), 2)}}


def run(url: str, scenario: str, conc: int, duration: float = 30, warmup: float = 5, procs: int | None = None,
        token: str | None = None, explain: str | None = None, source: str = "loadtest") -> dict:
    procs = procs or max(1, min(4, conc // 8 if conc >= 8 else 1))
    per = [conc // procs + (1 if i < conc % procs else 0) for i in range(procs)]
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    ps = [ctx.Process(target=_proc, args=((url, scenario, c, duration, warmup, 1000 + i, token, explain, source), q))
          for i, c in enumerate(per) if c > 0]
    for p in ps:
        p.start()
    parts = [q.get() for _ in ps]
    for p in ps:
        p.join()
    merged: dict[str, list] = {}
    for part in parts:
        for k, v in part["latencies"].items():
            merged.setdefault(k, []).extend(v)
    allv = [x for v in merged.values() for x in v]
    out = {"scenario": scenario, "url": url, "concurrency": conc, "client_procs": len(ps), "duration_s": duration,
           "warmup_s": warmup, "explain": explain, **summarize(allv, duration),
           "per_endpoint": {k: summarize(v, duration) for k, v in merged.items()}}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://nginx:8080")
    ap.add_argument("--scenario", default="transfer", choices=["transfer", "mixed", "text", "monolith"])
    ap.add_argument("-c", "--concurrency", type=int, nargs="+", default=[8])
    ap.add_argument("-d", "--duration", type=float, default=30)
    ap.add_argument("--warmup", type=float, default=5)
    ap.add_argument("--procs", type=int, default=None)
    ap.add_argument("--token", default=None)
    ap.add_argument("--explain", default=None, choices=[None, "auto", "always", "never"])
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default=None, help="append results to this JSON file (list)")
    a = ap.parse_args()
    results = []
    for c in a.concurrency:
        r = run(a.url, a.scenario, c, a.duration, a.warmup, a.procs, a.token, a.explain)
        r["label"] = a.label
        r["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        lat = r.get("latency_ms", {})
        print(f"[{a.label}] {a.scenario} c={c}: {r['rps']} req/s  p50={lat.get('p50')} p95={lat.get('p95')} "
              f"p99={lat.get('p99')} max={lat.get('max')} ms  errors={r['errors']}/{r['n']}", flush=True)
        results.append(r)
    if a.out:
        prev = json.load(open(a.out)) if os.path.exists(a.out) else []
        json.dump(prev + results, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
