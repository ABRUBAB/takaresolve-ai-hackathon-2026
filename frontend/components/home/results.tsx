"use client";

import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { NotebookFigures } from "@/components/trust/figures";
import { DotWaffle, RiskDial } from "@/components/trust/visuals";
import { NumberTicker } from "@/components/ui/number-ticker";
import type { MetricsSummary } from "@/lib/types";
import { usePublic } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

function Tile({ className, children, delay = 0, src }: { className?: string; children: ReactNode; delay?: number; src?: string }) {
  return (
    <motion.div
      className={cn("relative flex flex-col justify-between gap-6 overflow-hidden rounded-3xl border border-border bg-card p-6", className)}
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, delay, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {children}
      {src && (
        <span className={cn("absolute right-5 top-5 font-mono text-[9px] uppercase tracking-[0.14em]", src === "official" ? "text-volt-ink dark:text-volt" : "text-faint")}>
          {src === "official" ? "● Kaggle run" : "○ local build"}
        </span>
      )}
    </motion.div>
  );
}

function Column({ v, label, strong }: { v: number; label: string; strong?: boolean }) {
  return (
    <div className="flex h-full flex-1 flex-col items-center justify-end gap-2">
      <span className={cn("num font-mono text-sm", strong ? "font-semibold" : "text-muted-foreground")}>{Math.round(v * 100)}%</span>
      <motion.div
        className={cn("w-full rounded-t-2xl rounded-b-md", strong ? "bg-volt" : "bg-muted-foreground/30")}
        initial={{ height: 0 }}
        whileInView={{ height: `${Math.max(4, v * 100)}%` }}
        viewport={{ once: true }}
        transition={{ duration: 1.2, ease: [0.2, 0.8, 0.2, 1] }}
      />
      <span className="text-center text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function Results() {
  const q = usePublic<MetricsSummary>("/metrics/summary");
  const h = q.data?.summary.headline;
  const src = q.data?.sources ?? {};
  const a1 = h?.ai1;
  const a5 = h?.ai5;
  const a6 = h && typeof h.ai6 === "object" ? h.ai6 : null;
  const a7 = h?.ai7;
  const cov = a1 && typeof a1.conformal_coverage === "object" ? a1.conformal_coverage : null;
  const ratio = a1 && isNum(a1.recall_at_5pct_alert_rate) && isNum(a1.recall_at_5pct_rule_baseline) && a1.recall_at_5pct_rule_baseline > 0
    ? a1.recall_at_5pct_alert_rate / a1.recall_at_5pct_rule_baseline
    : null;
  const times = ratio ? (["", "", "Twice", "Three times", "Four times", "Five times"][Math.round(ratio)] ?? `${ratio.toFixed(1)}×`) : null;
  const ruleFa = (q.data?.per_ai.ai1 as { test_unseen_customers?: { rule_baseline?: { false_alerts_per_1000?: number } } } | null)?.test_unseen_customers?.rule_baseline?.false_alerts_per_1000;

  return (
    <section className="border-b border-border" aria-labelledby="results-title">
      <div className="mx-auto max-w-[1760px] px-4 py-24 md:px-8 xl:px-12 md:py-32">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label-mono">Measured, not claimed</p>
            <h2 id="results-title" className="mt-4 max-w-3xl font-serif text-5xl leading-[1] md:text-6xl">
              Same alert budget. <span className="italic">{times ? `${times} the scams caught.` : "More scams caught."}</span>
            </h2>
          </div>
          <Link href="/trust" className="inline-flex h-11 items-center gap-2 rounded-full border border-border px-5 text-sm hover:border-foreground/40">
            Every number <ArrowRight className="size-4" />
          </Link>
        </div>

        {q.warming && <p className="mt-10 text-sm text-muted-foreground">Waking the API… results appear in about a minute.</p>}
        {q.error && <p className="mt-10 text-sm text-muted-foreground">Results are not reachable right now; they are also in the README.</p>}

        {h && a1 && (
          <div className="mt-14 grid gap-4 md:grid-cols-6">
            <Tile className="md:col-span-3 md:row-span-2" src={src.ai1}>
              <p className="text-sm font-medium">Scams caught when 5 in 100 transfers are flagged</p>
              {isNum(a1.recall_at_5pct_alert_rate) && isNum(a1.recall_at_5pct_rule_baseline) && (
                <div className="flex h-64 items-end gap-6 px-4">
                  <Column v={a1.recall_at_5pct_alert_rate} label="UVERA AI-1" strong />
                  <Column v={a1.recall_at_5pct_rule_baseline} label="Simple rule" />
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                Tested on customers the model never saw (grouped split), in the weeks after training, against a simple rule (large amount to a
                new receiver) that flags the same number of transfers. PR-AUC {isNum(a1.pr_auc) ? a1.pr_auc.toFixed(2) : "—"} vs{" "}
                {isNum(a1.pr_auc_rule_baseline) ? a1.pr_auc_rule_baseline.toFixed(2) : "—"} for the rule.
              </p>
            </Tile>

            <Tile className="items-center text-center md:col-span-3 md:flex-row md:text-left" delay={0.05} src={src.ai1}>
              {cov && <RiskDial p={cov.overall} size={150} tone="safe" label="covered" />}
              <div>
                <p className="text-sm font-medium">Says “not sure” honestly</p>
                <p className="mt-1 text-sm text-muted-foreground">Conformal sets held the true answer {Math.round((cov?.overall ?? 0) * 100)}% of the time (target 90%).</p>
              </div>
            </Tile>

            <Tile className="md:col-span-3" delay={0.1} src={src.ai1}>
              <p className="text-sm font-medium">False alarms per 1,000 normal transfers</p>
              {isNum(a1.false_alerts_per_1000) && (
                <div className="flex items-end gap-4">
                  <p className="num font-serif text-7xl leading-none">
                    <NumberTicker value={a1.false_alerts_per_1000} decimalPlaces={1} />
                  </p>
                  {isNum(ruleFa) && (
                    <div className="mb-2 flex-1 space-y-2">
                      {[
                        ["UVERA", a1.false_alerts_per_1000, true],
                        ["Simple rule", ruleFa, false],
                      ].map(([k, v, strong]) => (
                        <div key={String(k)} className="flex items-center gap-2 text-xs">
                          <span className="w-16 text-muted-foreground">{String(k)}</span>
                          <div className="h-2 flex-1 rounded-full bg-muted">
                            <motion.div
                              className={cn("h-full rounded-full", strong ? "bg-foreground" : "bg-muted-foreground/40")}
                              initial={{ width: 0 }}
                              whileInView={{ width: `${(Number(v) / Math.max(Number(ruleFa), Number(a1.false_alerts_per_1000))) * 100}%` }}
                              viewport={{ once: true }}
                              transition={{ duration: 1 }}
                            />
                          </div>
                          <span className="num w-8 text-right font-mono">{Number(v).toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Tile>

            <Tile className="md:col-span-2" delay={0.05} src={src.ai5}>
              <p className="text-sm font-medium">QR Shield · the 20 shops checked each week</p>
              {isNum(a5?.precision_at_k) && <DotWaffle filled={Math.round(a5.precision_at_k * 20)} total={20} cols={10} />}
              <p className="text-sm text-muted-foreground">
                {isNum(a5?.precision_at_k) ? `${Math.round(a5.precision_at_k * 20)} of the 20 shops analysts review each week are real hidden cash-out` : "—"}
                {isNum(a5?.fpr_honest_round_price) ? `; honest round-price shops flagged ${(a5.fpr_honest_round_price * 100).toFixed(1)}%.` : "."}
              </p>
            </Tile>

            <Tile className="md:col-span-2" delay={0.1} src={src.ai6}>
              <p className="text-sm font-medium">Case Linker · analyst work</p>
              {a6 && isNum(a6.analyst_items_reduction) && (
                <p className="num font-serif text-7xl leading-none">−{Math.round(a6.analyst_items_reduction * 100)}%</p>
              )}
              <p className="text-sm text-muted-foreground">fewer items to open when alerts that share mule wallets or shops are reviewed as one case</p>
            </Tile>

            <Tile className="md:col-span-2" delay={0.15} src={src.ai7}>
              <p className="text-sm font-medium">Prompt-injection attacks shown to users</p>
              <p className="num font-serif text-7xl leading-none">
                {a7 && isNum(a7.injection_shown_success_rate) ? `${Math.round(Number(a7.injection_shown_success_rate) * 100)}%` : "—"}
              </p>
              <p className="text-sm text-muted-foreground">Gemini may only reword facts the models produced; a validator checks every number and evidence id and falls back to a template.</p>
            </Tile>
          </div>
        )}
        <NotebookFigures prefix={["summary_", "ai1_pr_curve", "ai1_shap"]} className="mt-12" />
        <Link href="/trust" className="mt-10 inline-flex items-center gap-1 text-sm font-medium underline-offset-4 hover:underline">
          All charts, fairness slices, calibration, model choice and limitations in the Trust Center <ArrowUpRight className="size-4" />
        </Link>
      </div>
    </section>
  );
}
