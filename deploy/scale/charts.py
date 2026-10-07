"""Charts for reports/scalability/README.md (matplotlib, PNG).  .venv\\Scripts\\python deploy/scale/charts.py"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "reports" / "scalability"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # categorical slots 1-3 (validated all-pairs, light mode)
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
                     "legend.frameon": False, "lines.linewidth": 2, "lines.markersize": 7})


def load(name: str):
    p = R / name
    return json.loads(p.read_text()) if p.exists() else []


def latency_and_throughput() -> None:
    rows = [r for r in load("loadtest_transfer.json") if r.get("replicas")]
    if not rows:
        return
    reps = sorted({r["replicas"] for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, q in zip(axes, ["p50", "p95", "p99"]):
        for i, n in enumerate(reps):
            pts = sorted((r["concurrency"], r["latency_ms"][q]) for r in rows if r["replicas"] == n)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=SERIES[i], label=f"{n} replica{'s' if n > 1 else ''}")
            ax.annotate(f"{pts[-1][1]:.0f}", pts[-1], textcoords="offset points", xytext=(6, -3), color=INK2, fontsize=8)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks([1, 8, 32, 64, 128], ["1", "8", "32", "64", "128"])
        ax.set_title(f"{q} latency", loc="left", fontsize=11)
        ax.set_xlabel("concurrent clients")
    axes[0].set_ylabel("ms (log scale)")
    axes[0].legend(loc="upper left")
    fig.suptitle("Transfer scoring latency vs concurrency, by scorer replica count (through nginx)", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(R / "latency_vs_concurrency.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for i, n in enumerate(reps):
        pts = sorted((r["concurrency"], r["rps"]) for r in rows if r["replicas"] == n)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=SERIES[i], label=f"{n} replica{'s' if n > 1 else ''}")
        best = max(pts, key=lambda p: p[1])
        ax.annotate(f"{best[1]:,.0f} req/s", best, textcoords="offset points", xytext=(-10, 8), color=INK2, fontsize=8)
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 8, 32, 64, 128], ["1", "8", "32", "64", "128"])
    ax.set_xlabel("concurrent clients")
    ax.set_ylabel("successful requests / s")
    ax.set_title("Throughput scaling with scorer replicas (1 vCPU each)", loc="left", fontsize=12)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(R / "throughput_scaling.png", dpi=130)
    plt.close(fig)


def before_after() -> None:
    mono = {r["concurrency"]: r for r in load("monolith_baseline.json")}
    stack = {r["concurrency"]: r for r in load("host_vs_monolith.json")}
    common = sorted(set(mono) & set(stack))
    if not common:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    w = 0.38
    xs = range(len(common))
    for k, (src, label, col) in enumerate([(mono, "monolith API (before)", SERIES[1]), (stack, "scale stack, 4 replicas (after)", SERIES[0])]):
        axes[0].bar([x + (k - 0.5) * w for x in xs], [src[c]["latency_ms"]["p99"] for c in common], w - 0.04, color=col, label=label)
        axes[1].bar([x + (k - 0.5) * w for x in xs], [src[c]["rps"] for c in common], w - 0.04, color=col, label=label)
        for x, c in zip(xs, common):
            axes[0].annotate(f"{src[c]['latency_ms']['p99']:.0f}", (x + (k - 0.5) * w, src[c]["latency_ms"]["p99"]), ha="center",
                             textcoords="offset points", xytext=(0, 3), fontsize=8, color=INK2)
            axes[1].annotate(f"{src[c]['rps']:.0f}", (x + (k - 0.5) * w, src[c]["rps"]), ha="center",
                             textcoords="offset points", xytext=(0, 3), fontsize=8, color=INK2)
    for ax, t, yl in [(axes[0], "p99 latency", "ms"), (axes[1], "throughput", "req/s")]:
        ax.set_xticks(list(xs), [f"c={c}" for c in common])
        ax.set_title(t, loc="left", fontsize=11)
        ax.set_ylabel(yl)
        ax.grid(axis="x", visible=False)
    axes[0].legend(loc="upper left")
    fig.suptitle("Before vs after: same client (Windows host), same transfers", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(R / "before_after.png", dpi=130)
    plt.close(fig)


def stream() -> None:
    rows = [r for r in load("stream_ingest.json") if r.get("n_workers") == 1 and r["target_rate"] != "max"]
    if not rows:
        return
    rows = sorted(rows, key=lambda r: r["target_rate"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    x = [r["target_rate"] for r in rows]
    axes[0].plot(x, x, color=GRID, linewidth=1.5, linestyle="--", label="target (ideal)")
    axes[0].plot(x, [r["worker_events_per_s"] for r in rows], marker="o", color=SERIES[0], label="worker applied")
    axes[0].set_xlabel("producer target rate (events/s)")
    axes[0].set_ylabel("events/s")
    axes[0].set_title("Stream ingestion throughput (1 feature-worker)", loc="left", fontsize=11)
    axes[0].legend(loc="upper left")
    axes[1].plot(x, [r["lag_ms_p50_max_over_workers"] for r in rows], marker="o", color=SERIES[0], label="p50")
    axes[1].plot(x, [r["lag_ms_p95_max_over_workers"] for r in rows], marker="o", color=SERIES[1], label="p95")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("producer target rate (events/s)")
    axes[1].set_ylabel("ms (log)")
    axes[1].set_title("Produce -> feature store lag", loc="left", fontsize=11)
    axes[1].legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(R / "stream_ingest.png", dpi=130)
    plt.close(fig)


def drift() -> None:
    d = load("drift_demo.json")
    if not d:
        return
    phases = [p for p in d["phases"] if p["drift"]["status"] != "insufficient_data"]
    feats = list(phases[0]["drift"]["psi"])
    fig, ax = plt.subplots(figsize=(12, 4.6))
    w = 0.8 / len(phases)
    for k, p in enumerate(phases):
        vals = [p["drift"]["psi"][f] or 0 for f in feats]
        ax.bar([i + (k - (len(phases) - 1) / 2) * w for i in range(len(feats))], vals, w - 0.02, color=SERIES[k], label=p["name"])
    ax.axhline(0.1, color="#eda100", linewidth=1.2, linestyle="--")
    ax.axhline(0.2, color="#e34948", linewidth=1.2, linestyle="--")
    ax.annotate("warn 0.1", (len(feats) - 0.5, 0.1), textcoords="offset points", xytext=(0, 3), ha="right", fontsize=8, color=INK2)
    ax.annotate("alert 0.2", (len(feats) - 0.5, 0.2), textcoords="offset points", xytext=(0, 3), ha="right", fontsize=8, color=INK2)
    ax.set_yscale("symlog", linthresh=0.05)
    ax.set_xticks(range(len(feats)), feats, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("PSI vs training reference")
    ax.set_title("Feature drift per phase of the live stream", loc="left", fontsize=12)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(R / "drift_psi.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    latency_and_throughput()
    before_after()
    stream()
    drift()
    print("charts written to", R)
