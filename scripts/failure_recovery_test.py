"""Failure recovery and stale-artifact test against REAL API processes (Windows).

    python scripts/failure_recovery_test.py [--cycles 3] [--skip-stale]

Part A, crash recovery: starts the API with the production supervisor (scripts/start_api.ps1, the restart loop the demo
PC runs) on a free port, waits until /v1/health/ready is 200, records one case decision (audit row), then kills the
uvicorn process N times. For each kill it measures: how a request during the outage fails (connection refused, and how
fast) vs hanging; how fast /v1/demo answers 503 "warming_up" while the engines reload; the time until the port is open
again and until ready=200; and that the audit hash chain is still intact after the crash.

Part B, stale artifact: starts uvicorn directly with MODEL_DIR pointing at a copy of artifacts/ in which one byte of
ai1/model.txt is flipped -> /v1/health/ready must be 503 naming that file; then restores the byte, restarts, ready=200.

Writes reports/security/failure_recovery.json and .md. Uses a temp decision database, never the real one.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
OUT = ROOT / "reports" / "security"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http(base: str, path: str, method: str = "GET", body: dict | None = None, token: str | None = None, timeout: float = 10):
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("content-type", "application/json")
    if token:
        req.add_header("authorization", f"Bearer {token}")
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null"), time.perf_counter() - t, None
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read() or b"null")
        except json.JSONDecodeError:
            data = None
        return e.code, data, time.perf_counter() - t, None
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        kind = ("connection_refused" if isinstance(reason, ConnectionRefusedError) or "refused" in str(reason).lower()
                else "timeout" if "timed out" in str(reason).lower() else type(reason).__name__)
        return None, None, time.perf_counter() - t, kind


def wait_for(base: str, path: str, want: int, timeout: float, interval: float = 0.25):
    t0 = time.perf_counter()
    last = None
    while time.perf_counter() - t0 < timeout:
        st, data, _, err = http(base, path, timeout=5)
        last = (st, data, err)
        if st == want:
            return time.perf_counter() - t0, data
        time.sleep(interval)
    raise TimeoutError(f"{path} never returned {want} in {timeout}s; last: {last}")


def listener_pid(port: int) -> int | None:
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3] == "LISTENING":
            return int(parts[4])
    return None


def kill_tree(pid: int) -> None:
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)


def login(base: str, role: str = "ops") -> str:
    st, data, _, err = http(base, "/v1/auth/demo-login", "POST", {"role": role})
    if st != 200:
        raise RuntimeError(f"demo login failed: {st} {data} {err}")
    return data["token"]


# ------------------------------------------------------------------ part A
def crash_recovery(cycles: int, tmp: Path) -> dict:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "DB_PATH": str(tmp / "recovery.db"), "PYTHONIOENCODING": "utf-8", "LLM_MODE": "cached"}
    log = tmp / "api_supervisor.log"
    ps = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "start_api.ps1"),
                           "-Port", str(port), "-Log", str(log)], env=env, cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    result = {"supervisor": "scripts/start_api.ps1 (restart loop, 5 s pause)", "port": port, "cycles": []}
    try:
        t_first, _ = wait_for(base, "/v1/health/ready", 200, 400)
        result["first_start_to_ready_s"] = round(t_first, 1)
        print(f"first start: ready after {t_first:.1f}s", flush=True)
        tok = login(base)
        demo = http(base, "/v1/demo", token=tok)[1]
        case = next(s["request"]["case_key"] for s in demo["scenarios"] if s["area"] == "ops")
        st, _, _, _ = http(base, f"/v1/cases/{case}/actions", "POST",
                           {"action": "request_evidence", "reason": "Recovery test: decision recorded before the crash"}, tok)
        audit_before = http(base, "/v1/ops/audit/verify", token=tok)[1]
        result["audit_before"] = {k: audit_before[k] for k in ("ok", "rows", "head_hash")}
        for i in range(1, cycles + 1):
            pid = listener_pid(port)
            assert pid, "no process listening"
            t_kill = time.perf_counter()
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            # wait until the socket is really closed, then probe like a client would during the outage
            while listener_pid(port) == pid and time.perf_counter() - t_kill < 10:
                time.sleep(0.05)
            probes = []
            for _ in range(3):
                st, _, dt, err = http(base, "/v1/health/live", timeout=10)
                probes.append({"status": st, "error": err, "seconds": round(dt, 3)})
                if st:
                    break
            t_port, _ = wait_for(base, "/v1/health/live", 200, 120, 0.1)
            port_open = time.perf_counter() - t_kill
            warm = http(base, "/v1/demo", timeout=10)
            t_ready, _ = wait_for(base, "/v1/health/ready", 200, 400)
            ready = time.perf_counter() - t_kill
            tok = login(base)  # the per-start random signing key changed: old tokens are now invalid (expected)
            audit_after = http(base, "/v1/ops/audit/verify", token=tok)[1]
            cyc = {"cycle": i, "killed_pid": pid,
                   "outage_probes": probes,
                   "outage_request_failed_fast": all(p["error"] == "connection_refused" and p["seconds"] < 5 for p in probes if p["status"] is None),
                   "warming_up_probe": {"status": warm[0], "body_status": (warm[1] or {}).get("detail", {}).get("status")
                                        if isinstance(warm[1], dict) and isinstance(warm[1].get("detail"), dict) else None,
                                        "seconds": round(warm[2], 3)},
                   "kill_to_port_open_s": round(port_open, 1), "kill_to_ready_s": round(ready, 1),
                   "audit_after": {k: audit_after[k] for k in ("ok", "rows", "head_hash")}}
            cyc["audit_chain_intact"] = audit_after["ok"] and audit_after["head_hash"] == result["audit_before"]["head_hash"]
            result["cycles"].append(cyc)
            print(f"cycle {i}: outage probe {probes[0]['error']} in {probes[0]['seconds']}s; port open after {port_open:.1f}s; "
                  f"ready after {ready:.1f}s; audit intact={cyc['audit_chain_intact']}", flush=True)
    finally:
        kill_tree(ps.pid)
        pid = listener_pid(port)
        if pid:
            kill_tree(pid)
    ready_times = [c["kill_to_ready_s"] for c in result["cycles"]]
    result["summary"] = {"cycles": len(ready_times), "kill_to_ready_s_min": min(ready_times), "kill_to_ready_s_max": max(ready_times),
                         "kill_to_ready_s_mean": round(sum(ready_times) / len(ready_times), 1),
                         "all_recovered": len(ready_times) == cycles,
                         "outage_requests_failed_fast": all(c["outage_request_failed_fast"] for c in result["cycles"]),
                         "audit_chain_intact_after_every_crash": all(c["audit_chain_intact"] for c in result["cycles"])}
    return result


# ------------------------------------------------------------------ part B
def start_uvicorn(port: int, env: dict, log: Path) -> subprocess.Popen:
    f = open(log, "ab")  # noqa: SIM115 - closed with the process
    return subprocess.Popen([str(PY), "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "backend"), "--host", "127.0.0.1",
                             "--port", str(port)], env=env, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)


def stale_artifact(tmp: Path) -> dict:
    arts = tmp / "art_copy" / "artifacts"
    shutil.copytree(ROOT / "artifacts", arts, ignore=shutil.ignore_patterns("_versions"))
    target = arts / "ai1" / "model.txt"
    original = target.read_bytes()
    data = bytearray(original)
    data[1000] ^= 0x01
    target.write_bytes(bytes(data))
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "MODEL_DIR": str(arts), "DB_PATH": str(tmp / "stale.db"), "PYTHONIOENCODING": "utf-8"}
    out = {"tampered_file": "ai1/model.txt (one bit flipped at byte 1000)", "port": port}
    p = start_uvicorn(port, env, tmp / "stale_api.log")
    try:
        t0 = time.perf_counter()
        wait_for(base, "/v1/health/live", 200, 60, 0.1)
        st, body, _, _ = http(base, "/v1/health/ready")
        while body and body.get("status") == "warming_up" and time.perf_counter() - t0 < 60:
            time.sleep(0.2)
            st, body, _, _ = http(base, "/v1/health/ready")
        out["tampered"] = {"ready_status": st, "status": body.get("status"), "bad_files": body.get("bad_files"),
                           "seconds_to_verdict": round(time.perf_counter() - t0, 1),
                           "model_endpoint_status": http(base, "/v1/demo")[0]}
        print(f"stale artifact: ready={st} {body.get('status')} bad_files={[b['path'] for b in body.get('bad_files') or []]}", flush=True)
    finally:
        kill_tree(p.pid)
    target.write_bytes(original)
    p = start_uvicorn(port, env, tmp / "stale_api.log")
    try:
        t, body = wait_for(base, "/v1/health/ready", 200, 400)
        out["restored"] = {"ready_status": 200, "seconds_to_ready": round(t, 1),
                           "all_verified": all(m["verified"] for m in body["models"].values()), "models": body["models"]}
        print(f"restored: ready=200 after {t:.1f}s, all verified={out['restored']['all_verified']}", flush=True)
    finally:
        kill_tree(p.pid)
    out["passed"] = (out["tampered"]["ready_status"] == 503 and out["tampered"]["status"] == "failed"
                     and [b["path"] for b in out["tampered"]["bad_files"]] == ["ai1/model.txt"]
                     and out["tampered"]["model_endpoint_status"] == 503 and out["restored"]["all_verified"])
    return out


def write_md(rep: dict) -> None:
    a = rep.get("crash_recovery")
    md = ["# Failure recovery and stale-artifact test", "",
          f"Generated by `python scripts/failure_recovery_test.py` on {rep['generated_at']} ({rep['platform']}). Real processes, "
          "temp decision database.", ""]
    if a:
        s = a["summary"]
        md += ["## A. Crash recovery (uvicorn killed, `scripts/start_api.ps1` restarts it)", "",
               f"First cold start to ready: **{a['first_start_to_ready_s']} s**. Kill-to-ready over {s['cycles']} kills: "
               f"min **{s['kill_to_ready_s_min']} s**, mean **{s['kill_to_ready_s_mean']} s**, max **{s['kill_to_ready_s_max']} s** "
               "(5 s supervisor pause + process start + world and model load).", "",
               "| Kill | Request during outage | Port open again | `/v1/demo` while warming | Ready (200) | Audit chain after crash |",
               "|---|---|---|---|---|---|"]
        for c in a["cycles"]:
            pr = c["outage_probes"][0]
            md.append(f"| {c['cycle']} | {pr['error'] or pr['status']} after {pr['seconds']} s | {c['kill_to_port_open_s']} s | "
                      f"{c['warming_up_probe']['status']} ({c['warming_up_probe']['body_status']}) in {c['warming_up_probe']['seconds']} s | "
                      f"{c['kill_to_ready_s']} s | ok={c['audit_after']['ok']}, rows={c['audit_after']['rows']}, "
                      f"head unchanged={c['audit_chain_intact']} |")
        md += ["", f"- All kills recovered without a human: **{s['all_recovered']}**.",
               f"- Requests during the outage failed fast with *connection refused* (no hanging client): **{s['outage_requests_failed_fast']}**. "
               "On Windows a refused loopback connection takes about 2 s because the TCP stack retries the SYN twice; on Linux it is immediate.",
               "- While the engines reload, model endpoints answer at once with 503 `warming_up` (clients can show a retry message).",
               f"- The decision recorded before the crashes is still there and the audit hash chain verifies after every crash: "
               f"**{s['audit_chain_intact_after_every_crash']}**.",
               "- Signing keys are random per start unless JWT_KEYS/JWT_KEYS_FILE is set, so old demo tokens get 401 after a restart "
               "and the website logs in again; with a configured keyring tokens survive restarts.", ""]
    b = rep.get("stale_artifact")
    if b:
        t, r = b["tampered"], b["restored"]
        md += ["## B. Stale / tampered model artifact", "",
               f"MODEL_DIR = a copy of `artifacts/` with {b['tampered_file']}.", "",
               f"- `/v1/health/ready` -> **{t['ready_status']} {t['status']}** after {t['seconds_to_verdict']} s, "
               f"`bad_files` = {[x['path'] + ': ' + x['problem'] for x in t['bad_files'] or []]}.",
               f"- Model endpoint `/v1/demo` -> **{t['model_endpoint_status']}** (the tampered model is never loaded or served).",
               f"- Byte restored, process restarted -> ready **200** after {r['seconds_to_ready']} s, every model verified: **{r['all_verified']}**.",
               f"- Result: **{'PASS' if b['passed'] else 'FAIL'}**.", ""]
    (OUT / "failure_recovery.md").write_text("\n".join(md), encoding="utf-8")


def main() -> int:
    if platform.system() != "Windows":
        print("This test drives scripts/start_api.ps1 and Windows tools (netstat, taskkill).")
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=3)
    ap.add_argument("--skip-stale", action="store_true")
    ap.add_argument("--skip-crash", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="uvera_recovery_"))
    rep = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "platform": platform.platform()}
    try:
        if not args.skip_crash:
            rep["crash_recovery"] = crash_recovery(args.cycles, tmp)
        if not args.skip_stale:
            rep["stale_artifact"] = stale_artifact(tmp)
    finally:
        (OUT / "failure_recovery.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
        write_md(rep)
        shutil.rmtree(tmp, ignore_errors=True)
    ok = (rep.get("crash_recovery", {}).get("summary", {}).get("all_recovered", args.skip_crash)
          and rep.get("stale_artifact", {}).get("passed", args.skip_stale))
    print("FAILURE RECOVERY:", "PASS" if ok else "FAIL", "->", OUT / "failure_recovery.md")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
