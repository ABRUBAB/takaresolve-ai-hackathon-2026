"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { NumberTicker } from "@/components/ui/number-ticker";
import type { MetricsSummary } from "@/lib/types";
import { usePublic } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

function Source({ s }: { s?: string }) {
  const official = s === "official";
  return (
    <span className={cn("font-mono text-[10px] uppercase tracking-[0.14em]", official ? "text-volt-ink dark:text-volt" : "text-faint")}>
      {official ? "Kaggle run · official" : s === "dev" ? "Local build · pending Kaggle" : "Not measured yet"}
    </span>
  );
}

function Card({ className, children, delay = 0 }: { className?: string; children: ReactNode; delay?: number }) {
  return (
    <motion.div
      className={cn("flex flex-col justify-between gap-6 rounded-3xl border border-border bg-card p-6", className)}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, delay, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {children}
    </motion.div>
  );
}

function Bar({ label, v, strong }: { label: string; v: number; strong?: boolean }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className={strong ? "font-medium" : "text-muted-foreground"}>{label}</span>
        <span className="num font-mono">{v.toFixed(2)}</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <motion.div
          className={cn("h-full rounded-full", strong ? "bg-volt" : "bg-foreground/30")}
          initial={{ width: 0 }}
          whileInView={{ width: `${v * 100}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: [0.2, 0.8, 0.2, 1] }}
        />
      </div>
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

  return (
    <section className="border-b border-border" aria-labelledby="results-title">
      <div className="mx-auto max-w-7xl px-4 py-24 md:px-6 md:py-32">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label-mono">Measured, not claimed</p>
            <h2 id="results-title" className="mt-4 max-w-3xl font-serif text-5xl leading-[1] md:text-6xl">
              Every number comes from a <span className="italic">notebook run</span>.
            </h2>
          </div>
          <p className="max-w-sm text-sm text-muted-foreground">
            Read live from the result files. Tested on customers the model never saw, against a simple rule baseline. Synthetic data:
            this shows the method works, not real-world accuracy.
          </p>
        </div>

        {q.warming && <p className="mt-10 text-sm text-muted-foreground">Starting the AI engines… results appear in about a minute.</p>}
        {q.error && <p className="mt-10 text-sm text-muted-foreground">Results are not reachable right now. They are also in the repository README.</p>}

        {h && a1 && (
          <div className="mt-14 grid gap-4 md:grid-cols-6">
            <Card className="md:col-span-4 md:row-span-2">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium">AI-1 Pause Check · scams caught at the same 5% alert rate</p>
                  <Source s={src.ai1} />
                </div>
              </div>
              {isNum(a1.recall_at_5pct_alert_rate) && isNum(a1.recall_at_5pct_rule_baseline) && (
                <div className="grid items-end gap-8 md:grid-cols-[auto_1fr]">
                  <p className="num font-serif text-[clamp(4.5rem,10vw,8rem)] leading-none tracking-tight">
                    <NumberTicker value={Math.round(a1.recall_at_5pct_alert_rate * 100)} />
                    <span className="text-[0.5em]">%</span>
                  </p>
                  <div className="space-y-4 pb-3">
                    <Bar label="UVERA AI-1 (LightGBM)" v={a1.recall_at_5pct_alert_rate} strong />
                    <Bar label="Simple rule: large amount to a new receiver" v={a1.recall_at_5pct_rule_baseline} />
                  </div>
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                Customers in the test set were never seen in training (group split), and the test weeks come after the training weeks.
              </p>
            </Card>
            <Card className="md:col-span-2" delay={0.05}>
              <p className="text-sm font-medium">Precision-recall AUC</p>
              {isNum(a1.pr_auc) && isNum(a1.pr_auc_rule_baseline) && (
                <div>
                  <p className="num font-mono text-5xl font-semibold tracking-tight">{a1.pr_auc.toFixed(2)}</p>
                  <p className="mt-1 text-sm text-muted-foreground">vs {a1.pr_auc_rule_baseline.toFixed(2)} for the rule</p>
                </div>
              )}
              <Source s={src.ai1} />
            </Card>
            <Card className="md:col-span-2" delay={0.1}>
              <p className="text-sm font-medium">False alerts per 1,000 normal transfers</p>
              {isNum(a1.false_alerts_per_1000) && (
                <p className="num font-mono text-5xl font-semibold tracking-tight">{a1.false_alerts_per_1000.toFixed(1)}</p>
              )}
              <p className="text-sm text-muted-foreground">at the &ldquo;pause&rdquo; threshold, frozen on validation weeks</p>
            </Card>
            <Card className="md:col-span-2" delay={0.05}>
              <p className="text-sm font-medium">Says &ldquo;not sure&rdquo; honestly</p>
              {typeof a1.conformal_coverage === "object" && (
                <p className="num font-mono text-5xl font-semibold tracking-tight">{Math.round(a1.conformal_coverage.overall * 100)}%</p>
              )}
              <p className="text-sm text-muted-foreground">
                conformal coverage (target 90%) · calibration error {isNum(a1.ece) ? a1.ece.toFixed(3) : "—"}
              </p>
            </Card>
            <Card className="md:col-span-2" delay={0.1}>
              <p className="text-sm font-medium">AI-5 QR Shield · top 20 per week</p>
              {isNum(a5?.precision_at_k) && <p className="num font-mono text-5xl font-semibold tracking-tight">{Math.round(a5.precision_at_k * 100)}%</p>}
              <p className="text-sm text-muted-foreground">
                of the shops analysts review are real hidden cash-out
                {isNum(a5?.fpr_honest_round_price) && ` · honest round-price shops flagged ${(a5.fpr_honest_round_price * 100).toFixed(1)}%`}
              </p>
              <Source s={src.ai5} />
            </Card>
            <Card className="md:col-span-2" delay={0.15}>
              <p className="text-sm font-medium">AI-6 Case Linker · analyst work</p>
              {a6 && isNum(a6.analyst_items_reduction) && (
                <p className="num font-mono text-5xl font-semibold tracking-tight">−{Math.round(a6.analyst_items_reduction * 100)}%</p>
              )}
              <p className="text-sm text-muted-foreground">fewer items to open when linked alerts are reviewed as one case</p>
              <Source s={src.ai6} />
            </Card>
            <Card className="md:col-span-6 md:flex-row md:items-center" delay={0.05}>
              <div>
                <p className="text-sm font-medium">AI-7 Grounded Brief · prompt-injection tests</p>
                <p className="mt-1 max-w-xl text-sm text-muted-foreground">
                  Gemini may only reword facts the models produced. A validator checks every number and evidence id; anything new is
                  rejected and a template is shown instead.
                </p>
              </div>
              <div className="flex items-baseline gap-3">
                <p className="num font-mono text-5xl font-semibold tracking-tight">
                  {a7 && isNum(a7.injection_shown_success_rate) ? `${Math.round(a7.injection_shown_success_rate * 100)}%` : "—"}
                </p>
                <p className="text-sm text-muted-foreground">of attacks reached a user</p>
              </div>
            </Card>
          </div>
        )}
        <Link href="/trust" className="mt-10 inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline">
          Open the Trust Center: every metric, fairness slice and limitation <ArrowUpRight className="size-4" />
        </Link>
      </div>
    </section>
  );
}
