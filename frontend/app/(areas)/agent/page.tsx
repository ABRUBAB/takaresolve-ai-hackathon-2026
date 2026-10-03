"use client";

import { ChevronDown, Store } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AreaIntro } from "@/components/customer/phone";
import { Guard } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { Inspector, InspectorSection, KV, SummaryChips, TraceFooter } from "@/components/trust/inspector";
import { pct, shortDate, tk } from "@/lib/format";
import type { Area as AreaT, Liquidity } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { usePalette } from "@/lib/use-palette";
import { cn } from "@/lib/utils";
import { TapHint } from "@/components/ui/tap-hint";

const tip = { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12, fontSize: 12 };
const k = (v: number) => `${Math.round(v / 1000)}k`;

export default function AgentPage() {
  const c = usePalette();
  const liq = useApi<Liquidity>("/agents/A0161/liquidity", "agent");
  const area = useApi<AreaT>("/agents/A0161/area", "agent");
  const [day, setDay] = useState<number | null>(null);
  const [more, setMore] = useState(true);

  return (
    <div className="mx-auto max-w-[1760px] px-4 py-8 md:px-8 xl:px-12 md:py-12">
      <AreaIntro
        label="Agent · Tanvir · AI-4 + AI-5 zone view"
        title={
          <>
            Cash for the week, <span className="italic">at a glance</span>.
          </>
        }
        text="Tanvir runs a cash-in / cash-out point near Rubab's home. Running out of cash turns customers away; holding too much is risky. Each column is how much cash to hold for a 90%-safe day; the bright part is the extra cash above what Tanvir usually holds."
      />
      <Guard q={liq}>
        {(l) => {
          const avgHold = l.forecast.reduce((s, f) => s + f.cash_to_hold_90pct_bdt, 0) / Math.max(1, l.forecast.length);
          const extra = Math.max(0, avgHold - l.capacity_bdt);
          const max = Math.max(...l.forecast.map((f) => f.cash_to_hold_90pct_bdt), l.capacity_bdt) * 1.08;
          const sel = day != null ? l.forecast[day] : null;
          const chart = [
            ...l.history.slice(-21).map((h) => ({ date: shortDate(h.date), actual: h.cash_out })),
            ...l.forecast.map((f) => ({ date: shortDate(f.date), band: [f.q10, f.q90] as [number, number], q50: f.q50 })),
          ];
          const peerPos = Math.min(1, Math.max(0, (l.peers.mine_last_28d - l.peers.p25) / Math.max(1, l.peers.p75 - l.peers.p25)));
          return (
            <div className="mt-8 space-y-8">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <p className="text-lg text-muted-foreground">
                  This week: hold about <span className="num font-mono font-semibold text-foreground">{tk(Math.round(avgHold / 500) * 500)}</span> a day
                  {extra > 0 && (
                    <>
                      {" "}
                      — <span className="num font-mono text-foreground">{tk(Math.round(extra / 500) * 500)}</span> more than usual
                    </>
                  )}
                </p>
                <p className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <span className="h-3 w-3 rounded-sm bg-volt-ink dark:bg-volt" /> extra cash above usual
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 border-t-2 border-dashed border-risk" /> usual cash on hand
                  </span>
                </p>
              </div>

              {/* cash tanks: fill = cash to hold for a 90%-safe day */}
              <div id="cash" className="grid scroll-mt-24 grid-cols-7 gap-2 md:gap-3">
                {l.forecast.map((f, i) => {
                  const h = (f.cash_to_hold_90pct_bdt / max) * 100;
                  const cap = (l.capacity_bdt / max) * 100;
                  const base = Math.min(h, cap);
                  const on = day === i;
                  return (
                    <button key={f.date} onClick={() => setDay(on ? null : i)} aria-pressed={on} className="group flex flex-col items-center gap-2">
                      <div
                        className={cn(
                          "relative h-[clamp(220px,38vh,340px)] w-full overflow-hidden rounded-2xl border bg-card transition-all group-hover:-translate-y-1 group-hover:shadow-lg group-hover:shadow-black/20 md:rounded-3xl",
                          "border-border",
                          on && "ring-2 ring-foreground/60",
                        )}
                      >
                        {/* grey = cash Tanvir usually holds; volt = the extra the 90% forecast asks for */}
                        <motion.div
                          className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-muted-foreground/20 to-muted-foreground/45"
                          initial={{ height: 0 }}
                          animate={{ height: `${base}%` }}
                          transition={{ duration: 1, delay: i * 0.06, ease: [0.2, 0.8, 0.2, 1] }}
                        />
                        {h > cap && (
                          <motion.div
                            className="absolute inset-x-0 bg-gradient-to-t from-volt-ink/70 to-volt dark:from-volt/50 dark:to-volt"
                            style={{ bottom: `${cap}%` }}
                            initial={{ height: 0 }}
                            animate={{ height: `${h - cap}%` }}
                            transition={{ duration: 0.7, delay: 0.9 + i * 0.06, ease: [0.2, 0.8, 0.2, 1] }}
                          />
                        )}
                        <div className="absolute inset-x-0 border-t-2 border-dashed border-risk" style={{ bottom: `${cap}%` }} />
                        <p className="absolute inset-x-0 top-3 text-center"><span className="num rounded-full bg-background/85 px-2 py-0.5 font-mono text-xs font-semibold md:text-sm">{k(f.cash_to_hold_90pct_bdt)}</span></p>
                      </div>
                      <span className={cn("text-xs md:text-sm", on ? "font-semibold" : "text-muted-foreground group-hover:text-foreground")}>{f.weekday.slice(0, 3)}</span>
                    </button>
                  );
                })}
              </div>

              <AnimatePresence mode="wait">
                {sel ? (
                  <motion.div
                    key={sel.date}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="grid gap-3 rounded-3xl border border-border bg-card p-5 sm:grid-cols-4"
                  >
                    {[
                      [`${sel.weekday} ${shortDate(sel.date)}`, "day"],
                      [tk(sel.cash_to_hold_90pct_bdt), "cash to hold (90%-safe)"],
                      [`${tk(sel.q10)} – ${tk(sel.q90)}`, "likely cash-out range"],
                      [`+${tk(sel.topup_bdt)}`, "above usual cash on hand"],
                    ].map(([v, label]) => (
                      <div key={label}>
                        <p className="num font-mono text-lg font-semibold">{v}</p>
                        <p className="text-xs text-muted-foreground">{label}</p>
                      </div>
                    ))}
                  </motion.div>
                ) : (
                  <motion.div key="hint" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <TapHint>Tap any day to see its range and top-up</TapHint>
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="grid gap-4 md:grid-cols-2">
                <div id="peers" className="scroll-mt-24 rounded-3xl border border-border bg-card p-5">
                  <p className="text-sm font-medium">You vs {l.peers.n} similar agents</p>
                  <p className="num mt-3 font-mono text-3xl font-semibold">
                    {tk(l.peers.mine_last_28d)}
                    <span className="text-sm font-normal text-muted-foreground"> /day</span>
                  </p>
                  <div className="mt-5">
                    <div className="relative h-2 rounded-full bg-muted">
                      <span className="absolute inset-y-0 left-1/4 right-1/4 rounded-full bg-foreground/20" />
                      <motion.span
                        className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-foreground"
                        initial={{ left: "50%" }}
                        animate={{ left: `${25 + peerPos * 50}%` }}
                        transition={{ duration: 1 }}
                      />
                    </div>
                    <div className="mt-2 flex justify-between text-[11px] text-faint">
                      <span>quiet</span>
                      <span>
                        typical {k(l.peers.p25)}–{k(l.peers.p75)}
                      </span>
                      <span>busy</span>
                    </div>
                  </div>
                </div>
                <Guard q={area}>
                  {(a) => (
                    <div id="qr" className="scroll-mt-24 rounded-3xl border border-border bg-card p-5">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium">QR cash-out pressure in your area</p>
                        <Store className="size-4 text-muted-foreground" />
                      </div>
                      <div className="mt-3 h-28">
                        <ResponsiveContainer>
                          <BarChart data={a.qr.weeks} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
                            <XAxis dataKey="week" tick={{ fontSize: 10, fill: c.faint }} tickLine={false} axisLine={false} tickFormatter={(w) => `wk ${w}`} />
                            <YAxis tick={{ fontSize: 10, fill: c.faint }} tickLine={false} axisLine={false} />
                            <Tooltip contentStyle={tip} />
                            <Bar dataKey="flagged_merchants" name="Shops on the review or watch list" fill={c.bar} radius={[3, 3, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <p className="mt-2 text-xs text-faint">Zone level only: agents never see which shops are flagged.</p>
                    </div>
                  )}
                </Guard>
              </div>

              <div id="forecast" className="scroll-mt-24">
                <button
                  onClick={() => setMore((m) => !m)}
                  aria-expanded={more}
                  className="inline-flex h-11 items-center gap-2 rounded-full border border-border px-5 text-sm hover:border-foreground/40"
                >
                  {more ? "Hide the forecast chart" : "Show the forecast chart"}
                  <ChevronDown className={cn("size-4 transition-transform", more && "rotate-180")} />
                </button>
                <AnimatePresence initial={false}>
                  {more && (
                    <motion.section initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                      <div className="mt-4 rounded-3xl border border-border bg-card p-5">
                        <div className="flex flex-wrap items-baseline justify-between gap-3">
                          <p className="text-sm font-medium">Cash-out demand · last 3 weeks and the next 7 days (80% range)</p>
                          <OutputChip type="model" />
                        </div>
                        <div className="mt-4 h-72">
                          <ResponsiveContainer>
                            <ComposedChart data={chart} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
                              <CartesianGrid vertical={false} stroke={c.border} />
                              <XAxis dataKey="date" tick={{ fontSize: 11, fill: c.faint }} interval={3} tickLine={false} axisLine={false} />
                              <YAxis tick={{ fontSize: 11, fill: c.faint }} tickLine={false} axisLine={false} tickFormatter={k} />
                              <Tooltip contentStyle={tip} formatter={(v) => (Array.isArray(v) ? `${tk(Number(v[0]))} to ${tk(Number(v[1]))}` : tk(Number(v)))} />
                              <ReferenceLine y={l.capacity_bdt} stroke={c.risk} strokeDasharray="4 4" />
                              <Bar dataKey="actual" name="Actual" fill={c.bar} radius={[3, 3, 0, 0]} />
                              <Area dataKey="band" name="80% range" fill={c.volt} fillOpacity={0.22} stroke="none" />
                              <Line dataKey="q50" name="Most likely" stroke={c.fg} strokeWidth={2} dot={{ r: 3 }} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </motion.section>
                  )}
                </AnimatePresence>
              </div>

              <Inspector summary={<SummaryChips items={[["model", l.model], ["best on validation", l.validated_winner], ["results", l.source], ["usual cash", tk(l.capacity_bdt)]]} />}>
                <InspectorSection title="AI-4 forecast" chip={<OutputChip type="model" />}>
                  <KV
                    rows={[
                      ["Agent", `${l.display_name} · ${l.agent_id}`],
                      ["Area · size", `${l.zone} · ${l.size}`],
                      ["Model used here", l.model],
                      ["Best on validation weeks", l.validated_winner],
                      ["Result files", l.source],
                      ["Usual cash on hand", tk(l.capacity_bdt)],
                    ]}
                  />
                </InspectorSection>
                <InspectorSection title="Chance demand exceeds cash on hand" chip={<OutputChip type="model">Model estimate</OutputChip>}>
                  <KV rows={l.forecast.map((f) => [`${f.weekday.slice(0, 3)} ${shortDate(f.date)}`, pct(f.p_stockout)] as [string, string])} />
                  <p className="text-sm text-muted-foreground">
                    Shown for transparency only. On test weeks the model could not tell which day of an agent&apos;s week runs short better than
                    chance, so no day is flagged and no yes/no alarm is raised. What works is the cash amount: holding the 90% forecast cut days
                    short of cash from about 21% to 12%.
                  </p>
                </InspectorSection>
                <InspectorSection title="Cash to hold" chip={<OutputChip type="rule">Rule on model output</OutputChip>}>
                  <p className="text-sm text-muted-foreground">
                    Cash to hold = the 90th-percentile forecast, rounded to Tk 500. Top-up = how far that is above the usual cash on hand.
                  </p>
                  <p className="text-sm text-muted-foreground">
                    <OutputChip type="assumption" className="mr-1" /> Usual cash on hand is set to 1.5 × the agent&apos;s average daily cash-out,
                    because real float data is not available.
                  </p>
                </InspectorSection>
                <TraceFooter trace={l.trace_id} model={l.model_version} data={l.data_version} />
              </Inspector>
            </div>
          );
        }}
      </Guard>
    </div>
  );
}
