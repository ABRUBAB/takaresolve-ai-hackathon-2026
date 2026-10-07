"""Benchmark orchestrator (host side). Drives docker compose, runs the in-network load generator, samples
`docker stats` during every run and appends annotated results to reports/scalability/*.json.

  .venv\\Scripts\\python deploy/scale/bench.py sweep --replicas 1 2 4 --conc 1 8 32 64 128 --duration 30
  .venv\\Scripts\\python deploy/scale/bench.py mixed --replicas 4 --conc 32 64
  .venv\\Scripts\\python deploy/scale/bench.py dbmode --replicas 4 --conc 64
  .venv\\Scripts\\python deploy/scale/bench.py explain --replicas 4 --conc 64
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORTS = ROOT / "reports" / "scalability"


def dc(*args: str, env: dict | None = None, check: bool = True) -> str:
    e = {**os.environ, **(env or {})}
    p = subprocess.run(["docker", "compose", *args], cwd=HERE, capture_output=True, text=True, env=e)
    if check and p.returncode != 0:
        raise RuntimeError(f"docker compose {' '.join(args)} failed:\n{p.stdout}\n{p.stderr}")
    return p.stdout + p.stderr


def healthy_scorers() -> int:
    out = subprocess.run(["docker", "ps", "--filter", "name=uvera-scale-scorer", "--format", "{{.Status}}"],
                         capture_output=True, text=True).stdout
    return sum("(healthy)" in line for line in out.splitlines())


def scale(n: int, env: dict | None = None, recreate: bool = False) -> None:
    args = ["up", "-d", "--scale", f"scorer={n}"] + (["--force-recreate"] if recreate else ["--no-recreate"]) + ["scorer"]
    dc(*args, env=env)
    t0 = time.time()
    while healthy_scorers() != n and time.time() - t0 < 180:
        time.sleep(2)
    dc("restart", "nginx")  # nginx also re-resolves every 5 s; a restart makes the start of each run deterministic
    time.sleep(3)
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3)
            break
        except Exception:  # noqa: BLE001
            time.sleep(1)
    print(f"scorer replicas healthy: {healthy_scorers()}", flush=True)


def _mem_mb(s: str) -> float:
    m = re.match(r"([\d.]+)\s*([KMG]i?B)", s.split("/")[0].strip())
    if not m:
        return 0.0
    v, u = float(m.group(1)), m.group(2)
    return v * {"KiB": 1 / 1024, "KB": 1 / 1000, "MiB": 1, "MB": 1, "GiB": 1024, "GB": 1000}[u]


class StatsSampler(threading.Thread):
    def __init__(self, delay: float):
        super().__init__(daemon=True)
        self.delay, self.samples, self.stop_flag = delay, [], False

    def run(self):
        time.sleep(self.delay)
        while not self.stop_flag:
            out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{json .}}"], capture_output=True, text=True).stdout
            snap = {}
            for line in out.splitlines():
                try:
                    j = json.loads(line)
                except ValueError:
                    continue
                if not j["Name"].startswith("uvera-scale"):
                    continue
                snap[j["Name"]] = {"cpu_pct": float(j["CPUPerc"].rstrip("%") or 0), "mem_mb": round(_mem_mb(j["MemUsage"]), 1)}
            self.samples.append(snap)
            time.sleep(2)

    def summary(self) -> dict:
        names = sorted({n for s in self.samples for n in s})
        out = {}
        for n in names:
            vals = [s[n] for s in self.samples if n in s]
            out[n] = {"cpu_pct_mean": round(sum(v["cpu_pct"] for v in vals) / len(vals), 1),
                      "cpu_pct_max": round(max(v["cpu_pct"] for v in vals), 1),
                      "mem_mb_max": round(max(v["mem_mb"] for v in vals), 1)}
        return out


def loadtest(out_name: str, scenario: str, conc: int, duration: float, meta: dict, explain: str | None = None) -> dict:
    out = REPORTS / out_name
    before = json.loads(out.read_text()) if out.exists() else []
    sampler = StatsSampler(delay=5 + duration * 0.3)
    sampler.start()
    args = ["--profile", "tools", "run", "--rm", "loadgen", "python", "-m", "uvscale.loadtest", "--url", "http://nginx:8080",
            "--scenario", scenario, "-c", str(conc), "-d", str(duration), "--warmup", "5",
            "--out", f"/repo/reports/scalability/{out_name}"] + (["--explain", explain] if explain else [])
    log = dc(*args)
    sampler.stop_flag = True
    sampler.join(timeout=15)
    print(log.strip().splitlines()[-1], flush=True)
    rows = json.loads(out.read_text())
    new = rows[len(before):]
    for r in new:
        r.update(meta)
        r["docker_stats"] = sampler.summary()
    out.write_text(json.dumps(before + new, indent=1))
    return new[-1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sweep", "mixed", "dbmode", "explain"])
    ap.add_argument("--replicas", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--conc", type=int, nargs="+", default=[1, 8, 32, 64, 128])
    ap.add_argument("--duration", type=float, default=30)
    a = ap.parse_args()
    REPORTS.mkdir(parents=True, exist_ok=True)
    if a.mode == "sweep":
        for n in a.replicas:
            scale(n)
            for c in a.conc:
                loadtest("loadtest_transfer.json", "transfer", c, a.duration, {"replicas": n, "db_write": "batch", "explain_mode": "auto"})
    elif a.mode == "mixed":
        for n in a.replicas:
            scale(n)
            for c in a.conc:
                loadtest("loadtest_mixed.json", "mixed", c, a.duration, {"replicas": n, "db_write": "batch", "explain_mode": "auto"})
    elif a.mode == "dbmode":
        for mode in ["sync", "batch", "off"]:
            for n in a.replicas:
                scale(n, env={"DB_WRITE": mode}, recreate=True)
                for c in a.conc:
                    loadtest("loadtest_dbmode.json", "transfer", c, a.duration, {"replicas": n, "db_write": mode, "explain_mode": "auto"})
        scale(a.replicas[-1], env={"DB_WRITE": "batch"}, recreate=True)
    elif a.mode == "explain":
        for n in a.replicas:
            scale(n)
            for ex in ["always", "auto", "never"]:
                for c in a.conc:
                    loadtest("loadtest_explain.json", "transfer", c, a.duration, {"replicas": n, "db_write": "batch", "explain_mode": ex}, explain=ex)


if __name__ == "__main__":
    main()
