"use client";

import { Maximize2, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/** Charts saved by the Kaggle notebooks (copied by scripts/export_web_assets.py). */
const CAPTIONS: Record<string, string> = {
  "ai1_pr_curve.png": "AI-1 precision–recall on customers it never saw, against the simple rule",
  "ai1_reliability.png": "AI-1 calibration: predicted probability vs how often it was really a scam",
  "ai1_risk_coverage.png": "AI-1 error rate when the least certain cases are handed to a person",
  "ai1_shap_global.png": "AI-1 global importance: which signals push the score most (mean |TreeSHAP|)",
  "ai2_reliability.png": "AI-2 verdict calibration on the held-out writing style",
  "ai3_forecast_example.png": "AI-3 a 7-day cash-flow forecast with its 80% range",
  "ai3_shortfall_reliability.png": "AI-3 calibration of the 7-day shortfall probability",
  "ai4_forecast_example.png": "AI-4 a 7-day agent cash-out forecast with its 80% range",
  "ai4_stockout_reliability.png": "AI-4 calibration of the stock-out probability",
  "ai5_reliability.png": "AI-5 calibration of the QR cash-out probability",
  "ai5_unseen_family_D.png": "AI-5 on scheme D, which was never shown in training",
  "summary_recall_vs_rule.png": "Scams caught at the same 5% alert rate: UVERA vs the rule",
};

type Fig = { file: string; source: "official" | "dev" };
let manifest: Promise<Fig[]> | null = null;
const loadManifest = () =>
  (manifest ??= fetch("/figures/manifest.json")
    .then((r) => (r.ok ? r.json() : { figures: [] }))
    .then((d: { figures: Fig[] }) => d.figures)
    .catch(() => []));

export function NotebookFigures({ prefix, className }: { prefix: string | string[]; className?: string }) {
  const [figs, setFigs] = useState<Fig[]>([]);
  const [open, setOpen] = useState<Fig | null>(null);
  const prefixes = Array.isArray(prefix) ? prefix : [prefix];
  const key = prefixes.join(",");

  useEffect(() => {
    let alive = true;
    loadManifest().then((all) => alive && setFigs(all.filter((f) => key.split(",").some((p) => f.file.startsWith(p)))));
    return () => {
      alive = false;
    };
  }, [key]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!figs.length) return null;
  return (
    <div className={className}>
      <p className="label-mono mb-3">Figures from the notebook · tap to enlarge</p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {figs.map((f) => (
          <button
            key={f.file}
            onClick={() => setOpen(f)}
            className="group overflow-hidden rounded-2xl border border-border bg-white text-left transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-black/30"
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- static PNGs from the notebooks, already sized */}
            <img src={`/figures/${f.file}`} alt={CAPTIONS[f.file] ?? f.file} loading="lazy" className="aspect-[4/3] w-full object-contain p-2" />
            <div className="flex items-start justify-between gap-2 border-t border-black/10 bg-neutral-50 px-3 py-2">
              <span className="text-xs leading-snug text-neutral-700">{CAPTIONS[f.file] ?? f.file}</span>
              <span className="flex shrink-0 items-center gap-1">
                <span className={cn("rounded-full px-1.5 py-0.5 font-mono text-[9px] uppercase", f.source === "official" ? "bg-lime-200 text-lime-900" : "bg-neutral-200 text-neutral-600")}>
                  {f.source === "official" ? "Kaggle" : "local"}
                </span>
                <Maximize2 className="size-3.5 text-neutral-500 group-hover:text-neutral-900" />
              </span>
            </div>
          </button>
        ))}
      </div>
      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-[90] grid place-items-center bg-black/80 p-4 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(null)}
            role="dialog"
            aria-modal="true"
            aria-label={CAPTIONS[open.file] ?? open.file}
          >
            <motion.figure
              className="relative max-h-[90vh] w-full max-w-4xl overflow-auto rounded-3xl bg-white p-4"
              initial={{ scale: 0.96 }}
              animate={{ scale: 1 }}
              onClick={(e) => e.stopPropagation()}
            >
              <button onClick={() => setOpen(null)} aria-label="Close" className="absolute right-3 top-3 grid size-9 place-items-center rounded-full bg-black text-white">
                <X className="size-4" />
              </button>
              {/* eslint-disable-next-line @next/next/no-img-element -- static PNGs from the notebooks */}
              <img src={`/figures/${open.file}`} alt={CAPTIONS[open.file] ?? open.file} className="mx-auto w-full" />
              <figcaption className="mt-2 text-center text-sm text-neutral-700">
                {CAPTIONS[open.file] ?? open.file} · {open.source === "official" ? "official Kaggle run" : "local build, Kaggle run pending"}
              </figcaption>
            </motion.figure>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
