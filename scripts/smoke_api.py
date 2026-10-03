"""Call every API endpoint once against a running server and print a short report.

    python scripts/smoke_api.py http://127.0.0.1:8000            # read-only
    python scripts/smoke_api.py http://127.0.0.1:8000 --write    # also records one case decision
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = (ARGS[0] if ARGS else "http://127.0.0.1:8000").rstrip("/") + "/v1"


def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode("utf-8") if body is not None else None)
    req.add_header("content-type", "application/json; charset=utf-8")
    if token:
        req.add_header("authorization", f"Bearer {token}")
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8")), time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")[:300], time.time() - t


def main():
    ok = True
    tok = {r: call("POST", "/auth/demo-login", body={"role": r})[1]["token"] for r in ("customer", "agent", "ops")}
    _, demo, _ = call("GET", "/demo", tok["customer"])
    sc = {s["id"]: s for s in demo["scenarios"]}
    for sid, s in sc.items():
        req = s["request"]
        if s["area"] == "customer":
            st, d, dt = call("POST", "/pause-check", tok["customer"], req)
            line = (f"{d['risk_level']:<6} {d['state']:<28} p={d['calibrated_probability']:.3f} brief={d['brief']['source']}"
                    if st == 200 else d)
        elif s["area"] == "customer_text":
            st, d, dt = call("POST", "/text-check", tok["customer"], req)
            line = f"{d['state']} p={d['p_scam']:.2f} {d['family']} ai_instructions={d['contains_ai_instructions']}" if st == 200 else d
        elif s["area"] == "customer_guardian":
            st, d, dt = call("GET", f"/customers/{req['customer_id']}/cashflow?goal_bdt=30000&months=6", tok["ops"])
            line = f"p_shortfall={d['p_shortfall_7d']:.2f} plans={[p['monthly_bdt'] for p in d['savings_plans']]}" if st == 200 else d
        elif s["area"] == "agent":
            st, d, dt = call("GET", f"/agents/{req['agent_id']}/liquidity", tok["agent"])
            line = f"cap={d['capacity_bdt']:.0f} p_stockout={[round(x['p_stockout'], 2) for x in d['forecast']]}" if st == 200 else d
        elif s["area"] == "ops":
            st, d, dt = call("GET", f"/cases/{req['case_key']}", tok["ops"])
            line = f"{d['case_key']} score={d['score']} victims={d['victims']} nodes={len(d['graph']['nodes'])} brief={d['brief']['source']}" if st == 200 else d
        else:
            st, d, dt = call("GET", f"/qr/merchants/{req['merchant_id']}", tok["ops"])
            line = f"{d['merchant_id']} {d['state']} p={d['p_calibrated']:.2f} peers={len(d['peer_comparison'])}" if st == 200 else d
        ok &= st == 200
        print(f"{st} {dt * 1000:6.0f} ms  {sid:<28} {line}")
    for path, role in [("/cases?limit=5", "ops"), ("/qr/merchants?limit=5", "ops"), ("/metrics/summary", "ops"),
                       ("/agents/" + demo["personas"]["agent"]["id"] + "/area", "agent"), ("/meta", "ops"), ("/web/world-sample", "ops"),
                       ("/customers/" + demo["personas"]["customer"]["id"] + "/profile", "customer")]:
        st, d, dt = call("GET", path, tok[role])
        ok &= st == 200
        print(f"{st} {dt * 1000:6.0f} ms  GET {path}")
    case = sc["ops_case"]["request"]["case_key"]
    if "--write" in sys.argv:  # opt-in: this records a decision in the case audit log (visible on the case page)
        st, d, _ = call("POST", f"/cases/{case}/actions", tok["ops"], {"action": "request_evidence", "reason": "Smoke test: ask the shop for sale evidence"})
        print(st, "POST action ->", d.get("status") if isinstance(d, dict) else d)
    st, _, _ = call("GET", "/cases", tok["customer"])
    print(st, "customer reading /cases (should be 403)")
    print("ALL OK" if ok else "SOME FAILED")


if __name__ == "__main__":
    main()
