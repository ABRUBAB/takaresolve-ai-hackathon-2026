"""Export the synthetic world into compact NumPy files for the stack's replay jobs (no pandas/pyarrow in the image).

    .venv\\Scripts\\python deploy/scale/offline/export_replay.py

_outputs/scale/replay_events.npz   events + security events, time-ordered, labels stripped (what an MFS core publishes)
_outputs/scale/customers.npz       customer master snapshot: registration day, opening ledger balance
_outputs/scale/ledger_sod.npz      daily start-of-day ledger balances (core-ledger snapshot, loaded once per day)
_outputs/scale/window_labels.npz   confirmed outcomes for test-window p2p transfers (joined in Postgres after the replay)
_outputs/scale/loadgen.json        20k real test-window transfers + 3k SMS texts used as load-test payloads
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
W = ROOT / "_outputs" / "world_full"
OUT = ROOT / "_outputs" / "scale"
ETYPES = ["salary_in", "remit_in", "cash_in", "p2p", "qr_pay", "bill_pay", "recharge", "cash_out", "device_change", "pin_reset"]
VAL_END = 100


def main() -> None:
    ev = pd.read_parquet(W / "events.parquet", columns=["event_id", "t", "etype", "src_kind", "src", "dst_kind", "dst", "amount",
                                                         "channel", "label_scam", "mule_flow"])
    ev["etype"] = ev["etype"].astype(str)
    sec = pd.read_parquet(W / "security.parquet", columns=["customer_id", "t", "kind"])
    sec = pd.DataFrame({"event_id": -1, "t": sec["t"].to_numpy(), "etype": sec["kind"].astype(str).to_numpy(), "src_kind": 0,
                        "src": sec["customer_id"].to_numpy(), "dst_kind": -1, "dst": "", "amount": 0.0, "channel": "app",
                        "label_scam": 0, "mule_flow": 0})
    ev["_o"], sec["_o"] = 1, 0  # equal t: security events first (batch builder includes exact-time matches)
    allv = pd.concat([sec, ev], ignore_index=True).sort_values(["t", "_o", "event_id"], kind="stable").reset_index(drop=True)
    vocab, codes = np.unique(np.concatenate([allv["src"].to_numpy(str), allv["dst"].to_numpy(str)]), return_inverse=True)
    n = len(allv)
    np.savez_compressed(OUT / "replay_events.npz", event_id=allv["event_id"].to_numpy(np.int64), t=allv["t"].to_numpy(np.int64),
                        etype=allv["etype"].map({e: i for i, e in enumerate(ETYPES)}).to_numpy(np.int8),
                        sk=allv["src_kind"].to_numpy(np.int8), dk=allv["dst_kind"].to_numpy(np.int8),
                        src=codes[:n].astype(np.int32), dst=codes[n:].astype(np.int32), amount=allv["amount"].to_numpy(float),
                        ussd=(allv["channel"] == "ussd").to_numpy(np.int8), vocab=vocab.astype(str), etypes=np.array(ETYPES))
    print("replay events", n)

    cust = pd.read_parquet(W / "customers.parquet", columns=["customer_id", "registration_day"])
    dc = pd.read_parquet(W / "daily_customer.parquet", columns=["customer_id", "day", "balance_sod"])
    opening = dc.sort_values("day").groupby("customer_id")["balance_sod"].first()
    np.savez_compressed(OUT / "customers.npz", ids=cust["customer_id"].to_numpy(str), reg=cust["registration_day"].to_numpy(np.int64),
                        bal=cust["customer_id"].map(opening).fillna(0.0).to_numpy(float))
    # start-of-day ledger balances (what a core ledger publishes once per day), day x customer, NaN = no account yet
    pos = {c: i for i, c in enumerate(cust["customer_id"].tolist())}
    led = np.full((int(dc["day"].max()) + 1, len(cust)), np.nan)
    led[dc["day"].to_numpy(int), dc["customer_id"].map(pos).to_numpy(int)] = dc["balance_sod"].to_numpy(float)
    np.savez_compressed(OUT / "ledger_sod.npz", ids=cust["customer_id"].to_numpy(str), bal=led)

    p2p = ev[(ev["etype"] == "p2p") & (ev["src_kind"] == 0) & (ev["dst_kind"] == 0) & (ev["t"] >= VAL_END * 86400)]
    unseen = (p2p["src"].str.slice(1).astype(int) % 10) < 3  # uvera_ml.features.splits.is_test_entity
    np.savez_compressed(OUT / "window_labels.npz", event_id=p2p["event_id"].to_numpy(np.int64), label=p2p["label_scam"].to_numpy(np.int8),
                        mule=p2p["mule_flow"].to_numpy(np.int8), unseen=unseen.to_numpy(bool))
    print("window p2p", len(p2p), "scams", int(p2p["label_scam"].sum()))

    tr = pd.read_parquet(OUT / "loadgen_transfers.parquet")
    texts = pd.read_parquet(OUT / "loadgen_texts.parquet")["text"].tolist()
    json.dump({"transfers": [[s, d, float(a), int(t), c] for s, d, a, t, c in
                             zip(tr["src"], tr["dst"], tr["amount"], tr["t"], tr["channel"])], "texts": texts},
              open(OUT / "loadgen.json", "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
