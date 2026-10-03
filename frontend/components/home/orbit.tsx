"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Mark } from "@/components/brand/logo";
import { OutputChip } from "@/components/trust/chips";
import type { MetricsSummary } from "@/lib/types";
import { usePublic } from "@/lib/use-api";
import { useMotionPref } from "@/lib/motion-pref";
import { cn } from "@/lib/utils";
import { TapHint } from "@/components/ui/tap-hint";

/* eslint-disable @typescript-eslint/no-explicit-any -- metric files are free-form JSON written by the notebooks */
type J = any;

type Ai = { id: string; name: string; how: string; who: string; what: string; out: "model" | "rule" | "generated"; metric: (m: MetricsSummary) => [string, string] | null };

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const mase = (a: J) => {
  const rows = ((a?.backtest as J[]) ?? []).filter((r) => r.split === "test");
  const best = rows.find((r) => r.model === a?.winner_on_validation) ?? rows[0];
  const naive = rows.find((r) => r.model === "seasonal_naive");
  return best && naive ? ([`${best.mase.toFixed(2)}`, `forecast error (MASE) vs ${naive.mase.toFixed(2)} for the naive baseline`] as [string, string]) : null;
};

const cashToHold = (a: J) => {
  const c = a?.cash_to_hold_test as J | undefined;
  const ours = c?.forecast_q90?.days_short_of_cash;
  const usual = c?.usual_cash?.days_short_of_cash;
  return isNum(ours) && isNum(usual) ? ([`${Math.round(ours * 100)}%`, `of days short of cash when holding the forecast amount (usual cash: ${Math.round(usual * 100)}%)`] as [string, string]) : null;
};

const AIS: Ai[] = [
  {
    id: "AI-1", name: "Pause Check", how: "LightGBM vs XGBoost, CatBoost, logistic regression and a rule · grouped CV × 5 seeds · isotonic calibration · conformal “not sure” · TreeSHAP reasons", who: "Customer", out: "model",
    what: "Scores a transfer before it leaves and pauses it with reasons when it looks like a scam.",
    metric: (m) => {
      const h = m.summary.headline.ai1;
      if (!isNum(h.recall_at_5pct_alert_rate)) return null;
      const rule = isNum(h.recall_at_5pct_rule_baseline) ? ` (simple rule: ${Math.round(h.recall_at_5pct_rule_baseline * 100)}%)` : "";
      return [`${Math.round(h.recall_at_5pct_alert_rate * 100)}%`, `of scams caught at a 5% alert rate${rule}`];
    },
  },
  {
    id: "AI-2", name: "Scam Text Check", how: "TF-IDF vs BGE-M3 embeddings vs an evidential head · tested on a held-out writing style · phrase occlusion", who: "Customer", out: "model",
    what: "Reads an SMS in Bangla, Banglish or English, names the scam family and highlights the words that matter.",
    metric: (m) => {
      const served = (((m.per_ai.ai2 as J)?.test_heldout_style_B as J[]) ?? []).find((r) => r.model === "tfidf_lr");
      return isNum(served?.verdict_pr_auc) ? [served.verdict_pr_auc.toFixed(2), "PR-AUC on a writing style it never saw (served model)"] : null;
    },
  },
  { id: "AI-3", name: "Cash-Flow Guardian", how: "Seasonal-naive vs LightGBM-quantile vs Chronos-2 · rolling-origin backtest · empirical probability", who: "Customer", out: "model", what: "Forecasts the week of money in and out and warns early if the balance may run low.", metric: (m) => mase(m.per_ai.ai3) },
  { id: "AI-4", name: "Liquidity Copilot", how: "Quantile forecasts · interval coverage · no yes/no alarm where the evidence is weak", who: "Agent", out: "model", what: "Tells an agent how much cash to hold for a 90%-safe day.", metric: (m) => cashToHold(m.per_ai.ai4) ?? mase(m.per_ai.ai4) },
  {
    id: "AI-5", name: "QR Shield", how: "LightGBM + Isolation Forest rank fusion · unseen scheme tested separately · size-fairness check", who: "Operations · Agent zone", out: "model",
    what: "Finds shops whose QR payments look like hidden cash-out, compared with shops of the same type, area and size.",
    metric: (m) => (isNum(m.summary.headline.ai5.precision_at_k) ? [`${Math.round(m.summary.headline.ai5.precision_at_k * 100)}%`, "of the 20 shops reviewed each week are real cash-out"] : null),
  },
  {
    id: "AI-6", name: "Case Linker", how: "Time-respecting path tracing (≤ 3 hops, ≤ 48 h) · union-find linking · community detection", who: "Operations", out: "rule",
    what: "Follows money paths in time order and joins alerts that share wallets or shops into one case with a deadline clock.",
    metric: (m) => {
      const v = (m.summary.headline.ai6 as J)?.analyst_items_reduction;
      return isNum(v) ? [`−${Math.round(v * 100)}%`, "fewer items for analysts to open"] : null;
    },
  },
  {
    id: "AI-7", name: "Grounded Brief", how: "Gemini structured output · evidence-card retrieval · deterministic validator · template fallback · injection tests", who: "Everyone", out: "generated",
    what: "Writes a short Bangla and English brief using only the facts the other AIs produced; a validator rejects anything new.",
    metric: (m) => (isNum(m.summary.headline.ai7.injection_shown_success_rate) ? [`${Math.round(Number(m.summary.headline.ai7.injection_shown_success_rate) * 100)}%`, "of prompt-injection attacks reached a user"] : null),
  },
];

export function AiOrbit() {
  const q = usePublic<MetricsSummary>("/metrics/summary");
  const [pick, setPick] = useState(0);
  const [hover, setHover] = useState(false);
  const { animate } = useMotionPref();
  const ai = AIS[pick];
  const metric = q.data ? ai.metric(q.data) : null;
  const spin = animate && !hover;

  return (
    <section className="border-b border-border" aria-labelledby="orbit-title">
      <div className="mx-auto max-w-[1760px] px-4 py-24 md:px-8 xl:px-12 md:py-32">
        <p className="label-mono">Seven AIs · one trust layer</p>
        <h2 id="orbit-title" className="mt-4 max-w-2xl font-serif text-5xl leading-[1] md:text-6xl">
          Tap an AI to <span className="italic">look inside</span>.
        </h2>
        <TapHint className="mt-6">Tap an AI on the ring to open its card</TapHint>
        <div className="mt-10 grid items-center gap-12 lg:grid-cols-2">
          <div className="relative mx-auto aspect-square w-full max-w-[460px]" onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
            <div className="absolute inset-0 rounded-full border border-dashed border-border" />
            <div className="absolute inset-[22%] rounded-full border border-dashed border-border/70" />
            <div className="absolute inset-[38%] grid place-items-center rounded-full bg-foreground text-background shadow-[0_0_80px_-20px_var(--volt)]">
              <Mark className="size-1/2 text-background" />
            </div>
            <motion.div
              className="absolute inset-0"
              animate={{ rotate: spin ? 360 : undefined }}
              transition={{ duration: 80, repeat: Infinity, ease: "linear" }}
            >
              {AIS.map((a, i) => {
                const ang = (i / AIS.length) * Math.PI * 2 - Math.PI / 2;
                const on = i === pick;
                return (
                  <motion.button
                    key={a.id}
                    onClick={() => setPick(i)}
                    aria-pressed={on}
                    aria-label={`${a.id} ${a.name}`}
                    className={cn(
                      "absolute grid size-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border font-mono text-xs font-semibold transition-colors md:size-[72px]",
                      on ? "border-volt bg-volt text-black shadow-[0_0_40px_-6px_var(--volt)]" : "border-border bg-card hover:border-foreground/50",
                    )}
                    style={{ left: `${50 + Math.cos(ang) * 44}%`, top: `${50 + Math.sin(ang) * 44}%` }}
                    animate={{ rotate: spin ? -360 : undefined }}
                    transition={{ duration: 80, repeat: Infinity, ease: "linear" }}
                  >
                    {a.id}
                  </motion.button>
                );
              })}
            </motion.div>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={ai.id}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
              className="rounded-3xl border border-border bg-card p-7 md:p-9"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm text-volt-ink dark:text-volt">{ai.id}</span>
                <OutputChip type={ai.out} />
              </div>
              <h3 className="mt-3 text-3xl font-semibold tracking-[-0.02em]">{ai.name}</h3>
              <p className="mt-1 text-xs text-faint">{ai.who}</p>
              <p className="mt-4 leading-relaxed text-muted-foreground">{ai.what}</p>
              <p className="mt-4 rounded-2xl bg-muted/60 px-4 py-3 font-mono text-[11px] leading-relaxed text-muted-foreground">{ai.how}</p>
              <div className="mt-8 border-t border-border pt-6">
                {metric ? (
                  <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                    <span className="num font-mono text-5xl font-semibold tracking-tight md:text-6xl">{metric[0]}</span>
                    <span className="max-w-60 text-sm text-muted-foreground">{metric[1]}</span>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">{q.warming ? "Waking the API…" : "Result appears after its notebook run."}</p>
                )}
              </div>
              <div className="mt-6 flex items-center gap-4 text-sm">
                <Link href="/trust" className="inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline">
                  How it was measured <ArrowUpRight className="size-3.5" />
                </Link>
                <button onClick={() => setPick((pick + 1) % AIS.length)} className="text-muted-foreground hover:text-foreground">
                  Next AI →
                </button>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
