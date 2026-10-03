"""Record real API responses for every demo scenario into the website (snapshot mode).

The website uses these recorded responses whenever the live API is unreachable or still waking up, so the hosted demo
always works, even on free static hosting. Every recorded response is a genuine model output from this API.

    uvicorn app.main:app --port 8000        # in backend/, wait until /v1/health/ready says ready
    python scripts/export_snapshot.py        # writes frontend/public/data/snapshot.json
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def key(method: str, path: str, body: dict | None = None) -> str:
    """Same key the website builds: method, path, and the JSON body with sorted keys."""
    return f"{method} {path}" + (f" {json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False)}" if body is not None else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--cases", type=int, default=15, help="how many top cases to record in full")
    a = ap.parse_args()
    base = a.api.rstrip("/") + "/v1"

    def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                     headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))

    for _ in range(60):
        try:
            if call("GET", "/health/ready").get("status") == "ready":
                break
        except urllib.error.HTTPError:
            pass
        time.sleep(3)
    tok = {role: call("POST", "/auth/demo-login", {"role": role})["token"] for role in ("customer", "agent", "ops")}
    tok["customer:C000125"] = call("POST", "/auth/demo-login", {"role": "customer", "subject_id": "C000125"})["token"]

    snap: dict[str, dict] = {}

    def rec(method: str, path: str, role: str | None = None, body: dict | None = None) -> dict:
        out = call(method, path, body, tok[role] if role else None)
        snap[key(method, path, body)] = out
        return out

    demo = rec("GET", "/demo")
    rec("GET", "/meta")
    rec("GET", "/metrics/summary")
    for s in demo["scenarios"]:
        if s["area"] == "customer":
            rec("POST", "/pause-check", "customer", s["request"])
        elif s["area"] == "customer_text":
            rec("POST", "/text-check", "customer", s["request"])
    rec("GET", "/customers/C000021/profile", "customer")
    rec("GET", "/customers/C000021/cashflow?goal_bdt=30000&months=6", "customer")
    out = call("GET", "/customers/C000125/cashflow?goal_bdt=30000&months=6", None, tok["customer:C000125"])
    snap[key("GET", "/customers/C000125/cashflow?goal_bdt=30000&months=6")] = out
    rec("GET", "/agents/A0161/liquidity", "agent")
    rec("GET", "/agents/A0161/area", "agent")
    cases = rec("GET", "/cases?limit=60", "ops")
    keys = ["CASE-0001"] + [c["case_key"] for c in cases["cases"] if c["case_key"] != "CASE-0001"][: a.cases - 1]
    for k in keys:
        rec("GET", f"/cases/{k}", "ops")
    merchants = set()
    for state in (None, "red", "amber", "grey_review"):
        path = "/qr/merchants?limit=120" + (f"&state={state}" if state else "")
        lst = rec("GET", path, "ops")
        merchants |= {m["merchant_id"] for m in lst["merchants"] if m["state"] != "green"}
    merchants.add("M00120")
    for m in sorted(merchants):
        rec("GET", f"/qr/merchants/{m}", "ops")

    payload = {"recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "api_version": snap[key("GET", "/meta")].get("api_version"),
               "note": "Real responses recorded from the UVERA API for the demo scenarios (synthetic data).", "responses": snap}
    dest = ROOT / "frontend" / "public" / "data" / "snapshot.json"
    dest.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"{len(snap)} responses -> {dest.relative_to(ROOT)} ({dest.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
