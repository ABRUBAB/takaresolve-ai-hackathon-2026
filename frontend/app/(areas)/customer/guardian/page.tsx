"use client";

import { AlertTriangle, Check, ShieldCheck } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { Area, Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AreaIntro, CustomerShell } from "@/components/customer/phone";
import { Guard } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { RiskDial } from "@/components/trust/visuals";
import { Inspector, InspectorSection, KV, SummaryChips, TraceFooter } from "@/components/trust/inspector";
import { pct, shortDate, tk } from "@/lib/format";
import { useLang } from "@/lib/i18n";
import type { Cashflow, SavingsPlan } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { usePalette } from "@/lib/use-palette";
import { cn } from "@/lib/utils";

const WHO = [
  { id: "C000021", label: "Rubab" },
  { id: "C000125", label: "A customer about to run short" },
];

const PLAN: Record<string, string> = { safe: "Safe", balanced: "Balanced", ambitious: "Ambitious" };
const PLAN_NOTE: Record<string, string> = {
  safe: "holds in a bad month",
  balanced: "in between",
  ambitious: "needs a normal month",
};

/**
 * The monthly amounts come from the API (they depend only on the customer's free cash, not on the goal).
 * Months-to-goal and the deadline check are the same rule as savings_options() in ml/uvera_ml/models/forecasting.py,
 * applied here so a new goal updates instantly, also in the recorded demo.
 */
function forGoal(plans: SavingsPlan[], goal: number, months: number) {
  const need = goal / Math.max(1, months);
  return {
    need,
    plans: plans.map((p) => ({
      ...p,
      months_to_goal: p.monthly_bdt > 0 ? Math.ceil(goal / p.monthly_bdt) : null,
      meets_deadline: p.monthly_bdt >= need,
    })),
  };
}

function SavingsResult({ plans, goal, months }: { plans: SavingsPlan[]; goal: number; months: number }) {
  const { need, plans: rows } = forGoal(plans, goal, months);
  const top = Math.max(need, ...rows.map((p) => p.monthly_bdt), 1);
  return (
    <motion.div className="space-y-3" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
      <p className="rounded-2xl bg-muted/60 px-3 py-2 text-sm">
        To save <span className="num font-mono font-semibold">{tk(goal)}</span> in <span className="font-semibold">{months} {months === 1 ? "month" : "months"}</span>, put
        aside <span className="num font-mono font-semibold">{tk(Math.ceil(need))}</span> a month.
      </p>
      <ul className="space-y-3">
        {rows.map((p, i) => (
          <li key={p.plan} className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-2 text-sm">
              <span className="min-w-0">
                <span className="font-medium">{PLAN[p.plan] ?? p.plan}</span>
                <span className="text-xs text-muted-foreground"> · {PLAN_NOTE[p.plan] ?? ""}</span>
              </span>
              <span className="num shrink-0 font-mono">{p.monthly_bdt > 0 ? `${tk(p.monthly_bdt)}/mo` : "Tk 0"}</span>
            </div>
            <div className="relative h-2.5 rounded-full bg-muted">
              <motion.div
                className={cn("h-full rounded-full", p.meets_deadline ? "bg-safe" : "bg-muted-foreground/50")}
                initial={{ width: 0 }}
                animate={{ width: `${(p.monthly_bdt / top) * 100}%` }}
                transition={{ duration: 0.8, delay: 0.1 + i * 0.08, ease: [0.2, 0.8, 0.2, 1] }}
              />
              <span className="absolute -top-1 h-[18px] w-0.5 rounded-full bg-foreground" style={{ left: `calc(${(need / top) * 100}% - 1px)` }} aria-hidden="true" />
            </div>
            <p className={cn("flex items-center gap-1 text-xs", p.meets_deadline ? "text-safe" : "text-muted-foreground")}>
              {p.monthly_bdt <= 0 ? (
                "No room to save safely right now: a bad month leaves nothing spare"
              ) : p.meets_deadline ? (
                <>
                  <Check className="size-3.5" /> Reaches the goal in {p.months_to_goal} {p.months_to_goal === 1 ? "month" : "months"}, on time
                </>
              ) : (
                `Reaches the goal in ${p.months_to_goal} months, later than you wanted`
              )}
            </p>
          </li>
        ))}
      </ul>
      <p className="flex items-center gap-1.5 text-[11px] text-faint">
        <span className="inline-block h-3 w-0.5 rounded-full bg-foreground" aria-hidden="true" /> the amount you need each month · nothing is moved automatically
      </p>
    </motion.div>
  );
}

export default function GuardianPage() {
  const [who, setWho] = useState(WHO[0].id);
  const [goal, setGoal] = useState("30000");
  const [months, setMonths] = useState("6");
  const [applied, setApplied] = useState({ goal: 30000, months: 6, run: 0 });
  const subject = who === "C000021" ? undefined : who;
  const q = useApi<Cashflow>(`/customers/${who}/cashflow?goal_bdt=30000&months=6`, "customer", subject);
  const { t } = useLang();
  const pal = usePalette();

  return (
    <CustomerShell
      intro={
        <AreaIntro
          label="Customer · Cash-flow Guardian · AI-3"
          title={
            <>
              See a shortfall <span className="italic">coming</span>.
            </>
          }
          text="A 7-day forecast of money in and out with an honest range, the chance the balance ends the week below a safety floor, and a savings plan that leaves room for bad weeks."
        />
      }
      phone={
        <div className="space-y-5 pt-2">
          <div className="no-scrollbar flex gap-1.5 overflow-x-auto" role="radiogroup" aria-label="Customer">
            {WHO.map((w) => (
              <button
                key={w.id}
                role="radio"
                aria-checked={who === w.id}
                onClick={() => setWho(w.id)}
                className={cn("shrink-0 rounded-full border px-3 py-1 text-xs", who === w.id ? "border-foreground bg-foreground text-background" : "border-border text-muted-foreground")}
              >
                {w.label}
              </button>
            ))}
          </div>
          <Guard q={q}>
            {(c) => {
              const chart = [
                ...c.history.slice(-21).map((h) => ({ date: shortDate(h.date), net: h.net })),
                ...c.forecast.map((f) => ({ date: shortDate(f.date), band: [f.q10, f.q90] as [number, number], q50: f.q50 })),
              ];
              return (
                <div className="space-y-5">
                  <div>
                    <p className="text-sm text-muted-foreground">{t("balance")}</p>
                    <p className="num font-mono text-3xl font-semibold">{tk(c.balance_now_bdt)}</p>
                  </div>
                  <div className={cn("rounded-3xl p-4", c.warning ? "bg-caution/10" : "bg-safe/10")}>
                    <div className="flex items-center gap-2">
                      {c.warning ? <AlertTriangle className="size-5 text-caution" /> : <ShieldCheck className="size-5 text-safe" />}
                      <p className="font-medium">{c.warning ? "Your balance may run low this week" : "This week looks safe"}</p>
                    </div>
                    <RiskDial p={c.p_shortfall_7d} size={150} className="mx-auto mt-3" tone={c.warning ? "caution" : "safe"} label="chance of running low" />
                    <p className="mt-2 text-xs text-muted-foreground">Safety floor: {tk(c.floor_bdt)} at the end of the next 7 days.</p>
                  </div>
                  <div>
                    <p className="mb-2 text-sm font-medium">Money in minus out · last 3 weeks and {t("next_7_days").toLowerCase()}</p>
                    <div className="h-48">
                      <ResponsiveContainer>
                        <ComposedChart data={chart} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
                          <CartesianGrid vertical={false} stroke={pal.border} />
                          <XAxis dataKey="date" tick={{ fontSize: 9, fill: pal.faint }} interval={6} tickLine={false} axisLine={false} />
                          <YAxis tick={{ fontSize: 9, fill: pal.faint }} tickLine={false} axisLine={false} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                          <Tooltip
                            contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12, fontSize: 12 }}
                            formatter={(v) => (Array.isArray(v) ? `${tk(Number(v[0]))} to ${tk(Number(v[1]))}` : tk(Number(v)))}
                          />
                          <ReferenceLine y={0} stroke={pal.faint} />
                          <Bar dataKey="net" name="Actual" fill={pal.bar} radius={[2, 2, 0, 0]} />
                          <Area dataKey="band" name="80% range" fill={pal.volt} fillOpacity={0.25} stroke="none" />
                          <Line dataKey="q50" name="Most likely" stroke={pal.fg} dot={false} strokeWidth={2} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  <div className="space-y-4 rounded-3xl border border-border p-4">
                    <p className="font-medium">{t("savings_goal")}</p>
                    <form
                      className="flex items-end gap-2"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const g = Math.max(100, Number(goal) || 100);
                        const m = Math.min(60, Math.max(1, Number(months) || 1));
                        setGoal(String(g));
                        setMonths(String(m));
                        setApplied((a) => ({ goal: g, months: m, run: a.run + 1 }));
                      }}
                    >
                      <label className="flex-1 space-y-1 text-xs text-muted-foreground">
                        Goal (Tk)
                        <input inputMode="numeric" value={goal} onChange={(e) => setGoal(e.target.value.replace(/\D/g, ""))} className="h-10 w-full rounded-xl border border-border bg-background px-3 font-mono text-sm text-foreground" />
                      </label>
                      <label className="w-20 space-y-1 text-xs text-muted-foreground">
                        Months
                        <input inputMode="numeric" value={months} onChange={(e) => setMonths(e.target.value.replace(/\D/g, ""))} className="h-10 w-full rounded-xl border border-border bg-background px-3 font-mono text-sm text-foreground" />
                      </label>
                      <button type="submit" className="h-10 rounded-xl bg-foreground px-4 text-sm font-medium text-background transition-transform hover:scale-[1.03] active:scale-95">
                        Plan
                      </button>
                    </form>
                    <SavingsResult key={applied.run} plans={c.savings_plans} goal={applied.goal} months={applied.months} />
                  </div>
                </div>
              );
            }}
          </Guard>
        </div>
      }
      inspector={
        <Inspector
          summary={
            q.data ? (
              <SummaryChips items={[["model", q.data.model], ["best on validation", q.data.validated_winner], ["warning cut-off", pct(q.data.warning_threshold)]]} />
            ) : undefined
          }
        >
          {q.data ? (
            <>
              <InspectorSection title="AI-3 forecast" chip={<OutputChip type="model" />}>
                <KV
                  rows={[
                    ["Model used here", q.data.model],
                    ["Best on validation weeks", q.data.validated_winner],
                    ["Result files", q.data.source],
                    ["Event", q.data.event],
                    ["Probability method", q.data.probability_method],
                    ["Shortfall probability", pct(q.data.p_shortfall_7d, 1)],
                    ["Warning cut-off (chosen on validation)", pct(q.data.warning_threshold, 1)],
                  ]}
                />
                <p className="text-sm text-muted-foreground">
                  The probability is not made by adding daily quantiles. It comes from how real 7-day outcomes scattered around the forecast on
                  validation weeks, so it stays calibrated.
                </p>
              </InspectorSection>
              <InspectorSection title="Heaviest spending weeks" chip={<OutputChip type="model" />}>
                <KV rows={q.data.heavy_outflow_weeks.map((w) => [`Week of ${shortDate(w.week_start)}`, tk(w.outflow_bdt)] as [string, string])} />
              </InspectorSection>
              <InspectorSection title="Savings plan" chip={<OutputChip type="rule">Rule on model output</OutputChip>}>
                <KV
                  rows={[
                    ["Free cash per month (likely)", tk(q.data.monthly_free_cash.q50)],
                    ["Free cash per month (bad month, 10th pct.)", tk(q.data.monthly_free_cash.q10)],
                  ]}
                />
                <p className="text-sm text-muted-foreground">Free cash is resampled from the last 60 days. The safe plan saves 80% of the bad-month amount, so a weak month does not push the balance below the floor. Months to the goal = goal ÷ the monthly amount, rounded up; a plan is on time when its monthly amount covers goal ÷ months. Nothing is moved automatically.</p>
              </InspectorSection>
              <TraceFooter trace={q.data.trace_id} model={q.data.model_version} data={q.data.data_version} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Loading the forecast…</p>
          )}
        </Inspector>
      }
    />
  );
}
