"""After the last Kaggle results are in the repo, refresh everything the website and README read — in one command.

    python scripts/finalize.py
    git push

1. Results summary, model cards and fairness report (same code as NB99): rebuilt here when NB99's output is missing
   or older than any notebook result, so they always match the result files.
2. The API runs in-process (no server, no second terminal) and every response the website needs is recorded into
   frontend/public/data/snapshot.json (the hosted site plays these back when no live API is connected).
3. The homepage world sample and the notebook figures are copied into the website.
4. The results table in README.md is replaced with the current numbers.
5. One commit (nothing is pushed).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "ml"), str(ROOT / "backend"), str(ROOT / "scripts")]
os.environ.setdefault("UVERA_ROOT", str(ROOT))
os.environ["RATE_LIMIT_PER_MINUTE"] = "100000"  # the in-process recorder makes ~200 calls; the limit is for visitors
os.environ.setdefault("LLM_MODE", "cached")  # recordings use the stored briefs, never a live Gemini call


def step(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def summary_is_stale() -> bool:
    summary = ROOT / "reports" / "summary.md"
    if not summary.exists() or not (ROOT / "reports" / "model_cards" / "README.md").exists():
        return True
    newest = max(p.stat().st_mtime for p in (ROOT / "reports").glob("metrics_ai*.json"))
    return newest > summary.stat().st_mtime


def rebuild_summary() -> None:
    from uvera_ml.eval.report import build_summary

    s = build_summary(ROOT / "reports", ROOT, repo=ROOT)
    missing = [k for k, ok in s["available"].items() if not ok]
    print("summary, model cards and fairness report written" + (f" (not measured yet: {', '.join(missing)})" if missing else ""))


def record_snapshot() -> None:
    import export_snapshot
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        t0 = time.time()
        while True:
            r = client.get("/v1/health/ready")
            if r.status_code == 200 and r.json().get("status") == "ready":
                break
            if time.time() - t0 > 600:
                sys.exit(f"API did not become ready: {client.get('/v1/health/startup').json()}")
            time.sleep(2)
        print(f"API ready in {time.time() - t0:.0f} s")

        def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            r = client.request(method, "/v1" + path, json=body, headers=headers)
            if r.status_code >= 400:
                raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:200]}")
            return r.json()

        export_snapshot.write(export_snapshot.record(call))


def update_readme() -> None:
    summary = (ROOT / "reports" / "summary.md").read_text(encoding="utf-8")
    table = "\n".join(line for line in summary.splitlines() if line.startswith("|"))
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    start, end = "<!-- results:start -->", "<!-- results:end -->"
    if start not in readme or end not in readme:
        print("README has no results markers; skipped")
        return
    block = f"{start}\n{table}\n{end}"
    readme = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, readme, flags=re.S)
    readme_path.write_text(readme, encoding="utf-8")
    print("README results table updated")


def commit() -> None:
    paths = ["reports", "frontend/public", "README.md"]
    subprocess.run(["git", "-C", str(ROOT), "add", *paths], check=True)
    if subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"]).returncode == 0:
        print("Nothing changed; no commit needed.")
        return
    subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m",
                    "results: refresh website recordings, model cards and README from the final notebook results"], check=True)
    print("Committed. Now publish with:  git push")


def main() -> None:
    step("1/5 results summary, model cards, fairness report")
    if summary_is_stale():
        rebuild_summary()
    else:
        print("NB99 output is up to date; kept as is")
    step("2/5 recording the API responses for the website")
    record_snapshot()
    step("3/5 world sample and figures for the website")
    import export_web_assets

    export_web_assets.main()
    step("4/5 README results table")
    update_readme()
    step("5/5 commit")
    commit()


if __name__ == "__main__":
    main()
