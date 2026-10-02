"""Build every model artifact locally in quick mode, so the API and website can run without Kaggle.

The official results come from the Kaggle notebooks (artifacts/, reports/). This script writes a full, faster
development copy to _outputs/dev/ (not committed). The API uses artifacts/ first and falls back to _outputs/dev/.

    python scripts/build_dev_artifacts.py            # full-scale world, quick training (~5-10 min on a laptop)
    python scripts/build_dev_artifacts.py --scale small
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

import pandas as pd  # noqa: E402
from uvera_ml.common import read_json, write_json  # noqa: E402
from uvera_ml.eval.report import build_summary  # noqa: E402
from uvera_ml.graph.linker import run_ai6  # noqa: E402
from uvera_ml.models.ai1 import run_ai1  # noqa: E402
from uvera_ml.models.ai2 import run_ai2  # noqa: E402
from uvera_ml.models.ai5 import run_ai5  # noqa: E402
from uvera_ml.models.ai7 import run_ai7  # noqa: E402
from uvera_ml.models.forecasting import run_ai3, run_ai4  # noqa: E402
from uvera_ml.sim.report import web_sample, world_stats  # noqa: E402
from uvera_ml.sim.text import template_corpus  # noqa: E402
from uvera_ml.sim.world import load_or_generate  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="full", choices=["full", "small"])
    ap.add_argument("--out", default=str(ROOT / "_outputs" / "dev"))
    a = ap.parse_args()
    out = Path(a.out)
    t0 = time.time()

    def step(name):
        print(f"[{time.time() - t0:6.0f}s] {name}", flush=True)

    step("world")
    world = load_or_generate(ROOT / "_outputs" / f"world_{a.scale}", scale=a.scale)
    write_json(out / "reports" / "data_card_stats.json", world_stats(world))
    write_json(out / "artifacts" / "web" / "world_sample.json", web_sample(world))
    step("AI-1")
    run_ai1(world, out, quick=True)
    step("AI-5")
    run_ai5(world, out, quick=True)
    step("AI-3")
    run_ai3(world, out, n_customers=600, use_chronos=False)
    step("AI-4")
    run_ai4(world, out, use_chronos=False)
    step("AI-6")
    scored = pd.read_parquet(out / "artifacts" / "ai1" / "test_scores.parquet")
    merchants = pd.read_parquet(out / "artifacts" / "ai5" / "merchant_scores.parquet")
    run_ai6(world, out, scored, merchants)
    step("AI-2")
    run_ai2(out, template_corpus(per_template=40), None, use_bge=False, quick=True)
    step("AI-7")
    cases = json.loads((out / "artifacts" / "ai6" / "cases.json").read_text(encoding="utf-8"))
    run_ai7(out, scored, read_json(out / "artifacts" / "ai1" / "thresholds.json"), cases, gemini=None, n_eval=60, n_injection=12)
    step("summary")
    build_summary(out / "reports", out)
    step("done")


if __name__ == "__main__":
    main()
