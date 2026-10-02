"use client";

import { Info, Store } from "lucide-react";
import { motion } from "motion/react";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AreaIntro } from "@/components/customer/phone";
import { Guard } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { Inspector, InspectorSection, KV, TraceFooter } from "@/components/trust/inspector";
import { pct, shortDate, tk } from "@/lib/format";
import type { Area as AreaT, Liquidity } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { usePalette } from "@/lib/use-palette";
import { cn } from "@/lib/utils";

const tip = { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12, fontSize: 12 };
const k = (v: number) => `${Math.round(v / 1000)}k`;

export default function AgentPage() {
  const c = usePalette();
  const liq = useApi<Liquidity>("/agents/A0161/liquidity", "agent");
  const area = useApi<AreaT>("/agents/A0161/area", "agent");

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-12">
      <AreaIntro
        label="Agent · Karim · AI-4 Liquidity Copilot + AI-5 zone view"
        title={
          <>
            Enough cash for the week, <span className="italic">without guessing</span>.
          </>
        }
        text="Karim runs a cash-in / cash-out point near Rina's home. Running out of cash turns customers away; holding too much is risky. UVERA tells him how much to hold each day and which days need care."
      />
      <div className="mt-10 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_380px]">
        <Guard q={liq}>
          {(l) => {
            const chart = [
              ...l.history.slice(-21).map((h) => ({ date: shortDate(h.date), actual: h.cash_out })),
              ...l.forecast.map((f) => ({ date: shortDate(f.date), band: [f.q10, f.q90] as [number, number], q50: f.q50 })),
            ];
            const peerPos = Math.min(1, Math.max(0, (l.peers.mine_last_28d - l.peers.p25) / Math.max(1, l.peers.p75 - l.peers.p25)));
            return (
              <div className="space-y-6">
                <section className="rounded-3xl border border-border bg-card p-5 md:p-6">
                  <div className="flex flex-wrap items-baseline justify-between gap-3">
                    <h2 className="text-lg font-semibold">Cash-out demand · last 3 weeks and the next 7 days</h2>
                    <OutputChip type="model" />
                  </div>
                  <div className="mt-4 h-72">
                    <ResponsiveContainer>
                      <ComposedChart data={chart} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
                        <CartesianGrid vertical={false} stroke={c.border} />
                        <XAxis dataKey="date" tick={{ fontSize: 11, fill: c.faint }} interval={3} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: c.faint }} tickLine={false} axisLine={false} tickFormatter={k} />
                        <Tooltip
                          contentStyle={tip}
                          formatter={(v) => (Array.isArray(v) ? `${tk(Number(v[0]))} to ${tk(Number(v[1]))}` : tk(Number(v)))}
                        />
                        <ReferenceLine
                          y={l.capacity_bdt}
                          stroke={c.risk}
                          strokeDasharray="4 4"
                          label={{ value: "usual cash on hand", position: "insideTopLeft", fill: c.risk, fontSize: 11 }}
                        />
                        <Bar dataKey="actual" name="Actual" fill={c.bar} radius={[3, 3, 0, 0]} />
                        <Area dataKey="band" name="80% range" fill={c.volt} fillOpacity={0.22} stroke="none" />
                        <Line dataKey="q50" name="Most likely" stroke={c.fg} strokeWidth={2} dot={{ r: 3 }} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </section>

                <section>
                  <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
                    <h2 className="text-lg font-semibold">Cash to hold, day by day</h2>
                    <p className="text-sm text-muted-foreground">Enough for a 90%-safe day · riskiest days marked</p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
                    {l.forecast.map((f, i) => (
                      <motion.div
                        key={f.date}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className={cn("rounded-2xl border p-3", f.highlight ? "border-volt-ink bg-volt/10 dark:border-volt" : "border-border bg-card")}
                      >
                        <p className="text-sm font-medium">{f.weekday.slice(0, 3)}</p>
                        <p className="text-xs text-faint">{shortDate(f.date)}</p>
                        <p className="num mt-3 font-mono text-lg font-semibold leading-tight">{k(f.cash_to_hold_90pct_bdt)}</p>
                        <p className="text-[11px] text-muted-foreground">to hold</p>
                        <p className="num mt-2 font-mono text-xs">+{k(f.topup_bdt)} top-up</p>
                        {f.highlight && <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-volt-ink dark:text-volt">Riskiest</p>}
                      </motion.div>
                    ))}
                  </div>
                  <p className="mt-3 flex gap-2 text-sm text-muted-foreground">
                    <Info className="mt-0.5 size-4 shrink-0" />
                    {l.guidance}
                  </p>
                </section>

                <section className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-3xl border border-border bg-card p-5">
                    <h2 className="font-semibold">Compared with {l.peers.n} similar agents</h2>
                    <p className="mt-1 text-sm text-muted-foreground">Average daily cash-out, last 28 days</p>
                    <p className="num mt-4 font-mono text-3xl font-semibold">{tk(l.peers.mine_last_28d)}</p>
                    <p className={cn("text-sm", l.peers.change_pct < 0 ? "text-muted-foreground" : "text-caution")}>
                      {l.peers.change_pct >= 0 ? "+" : ""}
                      {l.peers.change_pct.toFixed(1)}% vs the previous 28 days
                    </p>
                    <div className="mt-5">
                      <div className="relative h-2 rounded-full bg-muted">
                        <span className="absolute inset-y-0 left-1/4 right-1/4 rounded-full bg-foreground/20" />
                        <span className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-foreground" style={{ left: `${25 + peerPos * 50}%` }} />
                      </div>
                      <div className="mt-2 flex justify-between text-[11px] text-faint">
                        <span>quiet</span>
                        <span>typical range {k(l.peers.p25)}–{k(l.peers.p75)}</span>
                        <span>busy</span>
                      </div>
                    </div>
                  </div>
                  <Guard q={area}>
                    {(a) => (
                      <div className="rounded-3xl border border-border bg-card p-5">
                        <div className="flex items-start justify-between gap-2">
                          <h2 className="font-semibold">QR cash-out pressure in your area</h2>
                          <Store className="size-4 text-muted-foreground" />
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">
                          Week {a.qr.latest.week}: {a.qr.latest.flagged_merchants} of {a.qr.latest.merchants} shops in the {a.zone.replace("_", "-")} zone are on QR Shieldshops in the {a.zone.replace("_", "-")} zone look like hidden cash-out.apos;s review or watch list.
                        </p>
                        <div className="mt-4 h-28">
                          <ResponsiveContainer>
                            <BarChart data={a.qr.weeks} margin={{ top: 4, right: 0, bottom: 0, left: -24 }}>
                              <XAxis dataKey="week" tick={{ fontSize: 10, fill: c.faint }} tickLine={false} axisLine={false} tickFormatter={(w) => `wk ${w}`} />
                              <YAxis tick={{ fontSize: 10, fill: c.faint }} tickLine={false} axisLine={false} />
                              <Tooltip contentStyle={tip} />
                              <Bar dataKey="flagged_merchants" name="Flagged shops" fill={c.bar} radius={[3, 3, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                        <p className="mt-3 text-xs text-faint">{a.qr.note}</p>
                      </div>
                    )}
                  </Guard>
                </section>
              </div>
            );
          }}
        </Guard>

        <div className="lg:sticky lg:top-20">
          <Inspector>
            {liq.data ? (
              <>
                <InspectorSection title="AI-4 forecast" chip={<OutputChip type="model" />}>
                  <KV
                    rows={[
                      ["Agent", `${liq.data.display_name} · ${liq.data.agent_id}`],
                      ["Area · size", `${liq.data.zone} · ${liq.data.size}`],
                      ["Model used here", liq.data.model],
                      ["Best on validation weeks", liq.data.validated_winner],
                      ["Result files", liq.data.source],
                      ["Usual cash on hand", tk(liq.data.capacity_bdt)],
                    ]}
                  />
                </InspectorSection>
                <InspectorSection title="Chance demand exceeds cash on hand" chip={<OutputChip type="model">Model estimate</OutputChip>}>
                  <KV rows={liq.data.forecast.map((f) => [`${f.weekday.slice(0, 3)} ${shortDate(f.date)}`, pct(f.p_stockout)] as [string, string])} />
                  <p className="text-sm text-muted-foreground">
                    Shown for transparency only. On test weeks these day-level probabilities were only modestly better than history, so the
                    app does not raise a yes/no stock-out alarm.
                  </p>
                </InspectorSection>
                <InspectorSection title="Cash to hold" chip={<OutputChip type="rule">Rule on model output</OutputChip>}>
                  <p className="text-sm text-muted-foreground">
                    Cash to hold = the 90th-percentile forecast, rounded to Tk 500. Top-up = how far that is above the usual cash on hand.
                  </p>
                  <p className="text-sm text-muted-foreground">
                    <OutputChip type="assumption" className="mr-1" /> Usual cash on hand is set to 1.5 × the agent&apos;s average daily
                    cash-out (configs/assumptions.yaml), because real float data is not available.
                  </p>
                </InspectorSection>
                <TraceFooter trace={liq.data.trace_id} model={liq.data.model_version} data={liq.data.data_version} />
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Loading…</p>
            )}
          </Inspector>
        </div>
      </div>
    </div>
  );
}
