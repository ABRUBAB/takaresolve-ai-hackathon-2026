"""Seed the online store with the customer master (registration day) and opening ledger balances.

In production this is the KYC/customer-master snapshot plus the ledger balance at go-live; afterwards everything
is kept current by the event stream.  python -m uvscale.bootstrap [--flush]
"""
from __future__ import annotations

import argparse
import os
import time

import numpy as np
import redis

DATA = os.environ.get("SCALE_DATA", "/repo/_outputs/scale")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flush", action="store_true", help="FLUSHDB first (fresh replay)")
    a = ap.parse_args()
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    if a.flush:
        r.flushdb()
    t0 = time.time()
    z = np.load(f"{DATA}/customers.npz")
    pipe = r.pipeline(transaction=False)
    for i, (cid, reg, bal) in enumerate(zip(z["ids"].tolist(), z["reg"].tolist(), z["bal"].tolist())):
        pipe.hset(f"c:{cid}", mapping={"reg": int(reg), "bal": float(bal)})
        if i % 2000 == 1999:
            pipe.execute()
    pipe.execute()
    print(f"bootstrapped {len(z['ids'])} wallets in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
