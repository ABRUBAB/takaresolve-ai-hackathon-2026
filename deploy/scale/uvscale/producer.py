"""Replay the synthetic event log (+ security events) into the Redis stream, in time order, at a target rate.

  python -m uvscale.producer --from-day 0 --to-day 100 --rate 0            # max speed (state warm-up)
  python -m uvscale.producer --from-day 100 --to-day 120 --rate 2500 --score-from-day 100 --end-marker
  python -m uvscale.producer --from-day 110 --to-day 115 --rate 5000 --shift amount_x3

Input: _outputs/scale/replay_events.npz (offline/export_replay.py). Labels are never sent: the stream carries only
what an MFS core would publish. Backpressure: if the consumer group falls more than --max-lag entries behind, the
producer waits (the stream is also capped with MAXLEN ~ so Redis memory stays bounded).
"""
from __future__ import annotations

import argparse
import os
import time

import numpy as np
import redis

DATA = os.environ.get("SCALE_DATA", "/repo/_outputs/scale")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
STREAM = os.environ.get("STREAM", "uvera:events")
GROUP = os.environ.get("GROUP", "features")


class Events:
    """Column arrays for a day range of the replay log."""

    def __init__(self, from_day: int, to_day: int):
        z = np.load(f"{DATA}/replay_events.npz", allow_pickle=False)
        t = z["t"]
        lo, hi = np.searchsorted(t, from_day * 86400, "left"), np.searchsorted(t, to_day * 86400, "left")
        self.vocab = z["vocab"].tolist()
        self.etypes = z["etypes"].tolist()
        self.event_id, self.t = z["event_id"][lo:hi], t[lo:hi]
        self.etype, self.sk, self.dk = z["etype"][lo:hi], z["sk"][lo:hi], z["dk"][lo:hi]
        self.src, self.dst = z["src"][lo:hi], z["dst"][lo:hi]
        self.amount, self.ussd = z["amount"][lo:hi].copy(), z["ussd"][lo:hi]
        self.dst_override: dict[int, str] = {}

    def __len__(self) -> int:
        return len(self.t)

    def p2p_mask(self) -> np.ndarray:
        return (self.etype == self.etypes.index("p2p")) & (self.sk == 0) & (self.dk == 0)

    def shift(self, kind: str, share: float, seed: int = 7) -> None:
        p2p = self.p2p_mask()
        if kind == "amount_x3":
            self.amount[p2p] *= 3
        elif kind == "new_receivers":  # money suddenly flows to wallets never seen before (no KYC record yet)
            idx = np.where(p2p & (np.random.default_rng(seed).random(len(self)) < share))[0]
            self.dst_override = {int(i): f"N{k:07d}" for k, i in enumerate(idx)}


class Ledger:
    """Daily start-of-day balance snapshot from the core ledger, written to the online store when a day starts."""

    def __init__(self):
        try:
            z = np.load(f"{DATA}/ledger_sod.npz")
            self.ids, self.bal = z["ids"].tolist(), z["bal"]
        except FileNotFoundError:
            self.ids, self.bal = None, None

    def load(self, r: redis.Redis, day: int) -> None:
        if self.ids is None or day >= len(self.bal) or r.exists(f"ledger:sod:{day}"):
            return
        row = self.bal[day]
        ok = ~np.isnan(row)
        mapping = {self.ids[i]: float(row[i]) for i in np.where(ok)[0]}
        pipe = r.pipeline(transaction=False)
        pipe.hset(f"ledger:sod:{day}", mapping=mapping)
        pipe.delete(f"ledger:sod:{day - 14}")  # retention 14 days: covers a worker that lags the producer
        pipe.execute()


LEDGER = Ledger()


def group_lag(r: redis.Redis) -> int:
    try:
        for g in r.xinfo_groups(STREAM):
            if g["name"] == GROUP:
                return int(g.get("lag") or 0)
    except redis.ResponseError:
        return 0
    return 0


def produce(r: redis.Redis, ev: Events, rate: float, score_from_day: int | None = None, max_seconds: float | None = None,
            start: int = 0, stop: int | None = None, maxlen: int = 400_000, max_lag: int = 150_000, chunk: int = 500) -> dict:
    stop = len(ev) if stop is None else min(stop, len(ev))
    V, E = ev.vocab, ev.etypes
    eid, tt, et, sk, dk = ev.event_id.tolist(), ev.t.tolist(), ev.etype.tolist(), ev.sk.tolist(), ev.dk.tolist()
    src, dst, amt, us = ev.src.tolist(), ev.dst.tolist(), ev.amount.tolist(), ev.ussd.tolist()
    p2p_code = E.index("p2p")
    score_t = None if score_from_day is None else score_from_day * 86400
    sent, t0, waited = start, time.time(), 0.0
    while sent < stop:
        now = time.time()
        if max_seconds and now - t0 >= max_seconds:
            break
        target = stop if rate <= 0 else min(stop, start + int(rate * (now - t0)) + 1)
        if target <= sent:
            time.sleep(0.002)
            continue
        if max_lag and (sent - start) % 20_000 < chunk and group_lag(r) > max_lag:
            w0 = time.time()
            while group_lag(r) > max_lag // 2:
                time.sleep(0.05)
            waited += time.time() - w0
        day = tt[sent] // 86400
        LEDGER.load(r, day)  # day boundary: start-of-day ledger snapshot lands before that day's events
        nxt = int(np.searchsorted(ev.t, (day + 1) * 86400, "left"))
        k = max(1, min(target - sent, chunk, nxt - sent))
        pipe = r.pipeline(transaction=False)
        pt = f"{time.time() * 1000:.3f}"
        for i in range(sent, sent + k):
            msg = {"id": eid[i], "t": tt[i], "e": E[et[i]], "sk": sk[i], "s": V[src[i]], "dk": dk[i],
                   "d": ev.dst_override.get(i) or V[dst[i]], "a": amt[i], "c": "u" if us[i] else "a", "pt": pt}
            if score_t is not None and tt[i] >= score_t and et[i] == p2p_code and sk[i] == 0 and dk[i] == 0:
                msg["x"] = 1
            pipe.xadd(STREAM, msg, maxlen=maxlen, approximate=True)
        pipe.execute()
        sent += k
    el = time.time() - t0
    return {"sent": sent - start, "seconds": round(el, 2), "rate_achieved": round((sent - start) / el, 1) if el else None,
            "target_rate": rate if rate > 0 else "max", "backpressure_wait_s": round(waited, 2), "next": sent}


def end_marker(r: redis.Redis) -> None:
    r.xadd(STREAM, {"e": "__end__", "pt": f"{time.time() * 1000:.3f}"}, maxlen=400_000, approximate=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-day", type=int, default=100)
    ap.add_argument("--to-day", type=int, default=120)
    ap.add_argument("--rate", type=float, default=2000, help="events/s, 0 = as fast as possible")
    ap.add_argument("--score-from-day", type=int, default=None, help="mark p2p transfers from this day for shadow scoring")
    ap.add_argument("--shift", choices=["none", "amount_x3", "new_receivers"], default="none")
    ap.add_argument("--shift-share", type=float, default=0.3)
    ap.add_argument("--max-seconds", type=float, default=None)
    ap.add_argument("--end-marker", action="store_true")
    a = ap.parse_args()
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    t0 = time.time()
    ev = Events(a.from_day, a.to_day)
    if a.shift != "none":
        ev.shift(a.shift, a.shift_share)
    print(f"loaded {len(ev)} events (days {a.from_day}-{a.to_day - 1}) in {time.time() - t0:.1f}s", flush=True)
    out = produce(r, ev, a.rate, a.score_from_day, a.max_seconds)
    if a.end_marker:
        end_marker(r)
    print(out, flush=True)


if __name__ == "__main__":
    main()
