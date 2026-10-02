"""Monochrome figures for the report and the Trust Center (matches DESIGN.md)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import precision_recall_curve  # noqa: E402

INK, MUTED, ACCENT = "#0A0A0A", "#8A8A8A", "#4D7C0F"


def _style(ax, title):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(alpha=0.25)


def reliability(curves: dict, path: str | Path, title: str = "Calibration (reliability)") -> None:
    fig, ax = plt.subplots(figsize=(4.6, 4.2), dpi=150)
    ax.plot([0, 1], [0, 1], ls="--", color=MUTED, lw=1, label="perfect")
    for (name, tbl), color in zip(curves.items(), [ACCENT, INK, MUTED]):
        ax.plot(tbl["mean_pred"], tbl["frac_pos"], marker="o", ms=3, color=color, label=name)
    ax.set_xlabel("predicted probability")
    ax.set_ylabel("observed frequency")
    ax.legend(frameon=False, fontsize=8)
    _style(ax, title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def pr_curves(series: dict, y, path: str | Path, title: str = "Precision-recall (test)") -> None:
    fig, ax = plt.subplots(figsize=(4.6, 4.2), dpi=150)
    for (name, s), color in zip(series.items(), [ACCENT, INK, MUTED, "#C2C2C2"]):
        p, r, _ = precision_recall_curve(y, s)
        ax.plot(r, p, color=color, lw=1.6, label=name)
    ax.set_xlabel("recall")
    ax.set_ylabel("precision")
    ax.legend(frameon=False, fontsize=8)
    _style(ax, title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def risk_coverage(tables: dict, path: str | Path, title: str = "Risk vs coverage (abstention)") -> None:
    fig, ax = plt.subplots(figsize=(4.6, 4.2), dpi=150)
    for (name, tbl), color in zip(tables.items(), [ACCENT, INK, MUTED]):
        ax.plot(tbl["coverage"], tbl["risk"], color=color, lw=1.6, label=name)
    ax.set_xlabel("coverage (share of cases decided automatically)")
    ax.set_ylabel("error rate among decided cases")
    ax.legend(frameon=False, fontsize=8)
    _style(ax, title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def bars(labels, values, path: str | Path, title: str, xlabel: str = "") -> None:
    fig, ax = plt.subplots(figsize=(5.2, 0.35 * len(labels) + 1.2), dpi=150)
    order = np.argsort(values)
    ax.barh(np.array(labels)[order], np.array(values)[order], color=INK)
    ax.set_xlabel(xlabel)
    _style(ax, title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def forecast_band(dates, actual, q10, q50, q90, path: str | Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=150)
    ax.fill_between(dates, q10, q90, color=MUTED, alpha=0.25, label="80% band")
    ax.plot(dates, q50, color=INK, lw=1.6, label="median forecast")
    ax.plot(dates, actual, color=ACCENT, lw=1.2, ls=":", marker="o", ms=2, label="actual")
    ax.legend(frameon=False, fontsize=8)
    _style(ax, title)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
