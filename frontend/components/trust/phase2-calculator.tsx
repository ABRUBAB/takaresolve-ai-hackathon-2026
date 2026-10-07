"use client";

import { AlertTriangle, CheckCircle2, ChevronDown, RotateCcw, TrendingDown, TrendingUp } from "lucide-react";
import { useId, useMemo, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Chart kind "calculator" (business.json, section "calculator"): the visitor sets every assumption and the
 * follow rate; the measured counts per 1 million transfers stay fixed. The arithmetic is the same as
 * economics() in scripts/phase2/business_case.py, and the file's `check` block is used as a self-test.
 */
export type CalculatorChart = {
  kind: "calculator";
  per_million: { scam_money_paused_bdt: number; false_pauses: number; unsure_reviews: number; alerts: number; linked_cases: number };
  transfers_per_month: number;
  assumptions: { key: string; label: string; unit: "min" | "bdt" | "pct"; low: number; base: number; high: number; pessimistic: "low" | "high" }[];
  follow_rate: { min: number; max: number; base: number };
  markers?: { label: string; value: number }[];
  check?: { follow_rate: number; net_benefit_bdt: number | null; break_even_follow_rate: number | null } | null;
};

/** Every assumption the formula uses; the calculator only renders when all of them are in the file. */
const KEYS = [
  "customer_minutes_lost_per_false_pause",
  "customer_value_per_minute_bdt",
  "support_contact_rate_per_false_pause",
  "support_contact_cost_bdt",
  "abandon_rate_after_false_pause",
  "fee_revenue_lost_per_abandoned_transfer_bdt",
  "analyst_cost_per_minute_bdt",
  "minutes_per_unsure_review",
  "minutes_per_alert_item",
  "minutes_per_linked_case",
  "server_cost_bdt_per_month",
] as const;
const PM_KEYS = ["scam_money_paused_bdt", "false_pauses", "unsure_reviews", "alerts", "linked_cases"] as const;
const PER = 1_000_000;

type Key = (typeof KEYS)[number];
type Values = Record<Key, number>;
type Unit = "min" | "bdt" | "pct" | "num";
type Step = number | "any";
type Assumption = { key: Key; label: string; unit: Unit; lo: number; hi: number; base: number; pess: number; opt: number; step: Step };
type Model = {
  pm: Record<(typeof PM_KEYS)[number], number>;
  perMonth: number;
  assumptions: Assumption[];
  follow: { min: number; max: number; base: number; step: Step };
  markers: { label: string; value: number }[];
  check: { f: number; net: number | null; be: number | null } | null;
};

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const asObj = (v: unknown): Record<string, unknown> | null => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null);
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const isKey = (k: unknown): k is Key => typeof k === "string" && (KEYS as readonly string[]).includes(k);

/** Largest "nice" step (1, 2 or 5 × 10^k) that hits low, base and high exactly and gives at least `minPositions` positions. */
function pickStep(lo: number, base: number, hi: number, minPositions: number): Step {
  const span = hi - lo;
  if (!(span > 0)) return "any";
  const exact = (x: number, s: number) => Math.abs(x / s - Math.round(x / s)) < 1e-6;
  const top = Math.ceil(Math.log10(span));
  for (let e = top; e >= top - 8; e--) {
    for (const m of [5, 2, 1]) {
      const s = m * 10 ** e;
      if (span / s >= minPositions && exact(span, s) && exact(base - lo, s)) return s;
    }
  }
  return "any";
}

/** Validates the JSON; anything missing or malformed returns null and the page shows "measuring…". */
function parse(raw: unknown): Model | null {
  const c = asObj(raw);
  const pmRaw = asObj(c?.per_million);
  if (!c || !pmRaw) return null;
  const pm = {} as Model["pm"];
  for (const k of PM_KEYS) {
    const v = pmRaw[k];
    if (!isNum(v) || v < 0) return null;
    pm[k] = v;
  }
  if (!(pm.scam_money_paused_bdt > 0)) return null;
  const perMonth = c.transfers_per_month;
  if (!isNum(perMonth) || perMonth <= 0) return null;

  const assumptions: Assumption[] = [];
  for (const item of Array.isArray(c.assumptions) ? c.assumptions : []) {
    const a = asObj(item);
    if (!a || !isKey(a.key) || assumptions.some((x) => x.key === a.key)) continue;
    if (!isNum(a.low) || !isNum(a.base) || !isNum(a.high)) continue;
    const lo = Math.min(a.low, a.high);
    const hi = Math.max(a.low, a.high);
    const base = clamp(a.base, lo, hi);
    const pessIsLow = a.pessimistic === "low";
    assumptions.push({
      key: a.key,
      label: typeof a.label === "string" && a.label.trim() ? a.label : a.key.replace(/_/g, " "),
      unit: a.unit === "min" || a.unit === "bdt" || a.unit === "pct" ? a.unit : "num",
      lo,
      hi,
      base,
      pess: pessIsLow ? a.low : a.high,
      opt: pessIsLow ? a.high : a.low,
      step: pickStep(lo, base, hi, 20),
    });
  }
  if (KEYS.some((k) => !assumptions.some((a) => a.key === k))) return null;

  const fr = asObj(c.follow_rate);
  if (!fr || !isNum(fr.min) || !isNum(fr.max) || !isNum(fr.base)) return null;
  const min = Math.max(0, fr.min);
  const max = Math.min(1, fr.max);
  if (!(max > min)) return null;
  const base = clamp(fr.base, min, max);

  const markers = (Array.isArray(c.markers) ? c.markers : [])
    .map(asObj)
    .filter((m): m is Record<string, unknown> => !!m && isNum(m.value) && typeof m.label === "string" && m.label.trim() !== "")
    .map((m) => ({ label: m.label as string, value: m.value as number }))
    .filter((m) => m.value >= min && m.value <= max);

  const ck = asObj(c.check);
  const check =
    ck && isNum(ck.follow_rate)
      ? { f: ck.follow_rate, net: isNum(ck.net_benefit_bdt) ? ck.net_benefit_bdt : null, be: isNum(ck.break_even_follow_rate) ? ck.break_even_follow_rate : null }
      : null;

  return { pm, perMonth, assumptions, follow: { min, max, base, step: pickStep(min, base, max, 400) }, markers, check };
}

/** economics() from scripts/phase2/business_case.py, plus the closed-form break-even (net is linear in f). */
function economics(m: Model, a: Values, f: number) {
  const pm = m.pm;
  const prevented = f * pm.scam_money_paused_bdt;
  const falsePauses =
    pm.false_pauses *
    (a.customer_minutes_lost_per_false_pause * a.customer_value_per_minute_bdt +
      a.support_contact_rate_per_false_pause * a.support_contact_cost_bdt +
      a.abandon_rate_after_false_pause * a.fee_revenue_lost_per_abandoned_transfer_bdt);
  const reviews = pm.unsure_reviews * a.minutes_per_unsure_review * a.analyst_cost_per_minute_bdt;
  const analyst = (pm.alerts * a.minutes_per_alert_item - pm.linked_cases * a.minutes_per_linked_case) * a.analyst_cost_per_minute_bdt; // can be negative
  const servers = a.server_cost_bdt_per_month * (PER / m.perMonth);
  const net = prevented + analyst - (falsePauses + reviews + servers);
  const rawBreakEven = (falsePauses + reviews + servers - analyst) / pm.scam_money_paused_bdt;
  const benefit = prevented + Math.max(analyst, 0);
  const cost = falsePauses + reviews + servers + Math.max(-analyst, 0);
  return { prevented, falsePauses, reviews, analyst, servers, net, rawBreakEven, breakEven: clamp(rawBreakEven, 0, 1), ratio: cost > 0 ? benefit / cost : null };
}

const PRESETS = [
  { id: "base", label: "Our base" },
  { id: "pess", label: "All pessimistic" },
  { id: "opt", label: "All optimistic" },
] as const;
type PresetId = (typeof PRESETS)[number]["id"];

function presetValues(m: Model, p: PresetId): Values {
  const out = {} as Values;
  for (const a of m.assumptions) out[a.key] = p === "base" ? a.base : p === "pess" ? a.pess : a.opt;
  return out;
}

/* ---------- formatting ---------- */

const trim = (v: number, digits: number) => v.toLocaleString("en-US", { maximumFractionDigits: digits });

function money(v: number, signed = false) {
  const r = Math.round(v);
  const sign = r < 0 ? "−" : signed && r > 0 ? "+" : "";
  return `${sign}Tk ${Math.abs(r).toLocaleString("en-US")}`;
}

/** Percent with 3 significant digits, trailing zeros dropped: 0.121%, 5.58%, 12%. */
function pct3(v: number) {
  const p = v * 100;
  if (p === 0) return "0%";
  const digits = clamp(2 - Math.floor(Math.log10(Math.abs(p))), 0, 4);
  return `${trim(p, digits)}%`;
}

function value(v: number, unit: Unit) {
  if (unit === "pct") return `${trim(v * 100, 1)}%`;
  if (unit === "bdt") return `Tk ${trim(v, 2)}`;
  if (unit === "min") return `${trim(v, 2)} min`;
  return trim(v, 2);
}

/* ---------- slider ---------- */

const RANGE = cn(
  "absolute inset-0 m-0 h-full w-full cursor-pointer appearance-none bg-transparent outline-none disabled:cursor-not-allowed disabled:opacity-40",
  "[&::-webkit-slider-runnable-track]:h-full [&::-webkit-slider-runnable-track]:bg-transparent",
  "[&::-webkit-slider-thumb]:mt-1.5 [&::-webkit-slider-thumb]:size-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-background [&::-webkit-slider-thumb]:bg-foreground [&::-webkit-slider-thumb]:transition-transform",
  "[&::-moz-range-track]:bg-transparent [&::-moz-range-thumb]:size-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-background [&::-moz-range-thumb]:bg-foreground",
  "hover:[&::-webkit-slider-thumb]:scale-110 active:[&::-webkit-slider-thumb]:scale-125",
  "focus-visible:[&::-webkit-slider-thumb]:outline-2 focus-visible:[&::-webkit-slider-thumb]:outline-offset-2 focus-visible:[&::-webkit-slider-thumb]:outline-ring",
  "focus-visible:[&::-moz-range-thumb]:outline-2 focus-visible:[&::-moz-range-thumb]:outline-offset-2 focus-visible:[&::-moz-range-thumb]:outline-ring",
);

/** Native range input (keyboard, touch and screen readers for free) over a drawn track. `children` decorate the track. */
function Range({
  id,
  value: v,
  min,
  max,
  step,
  onChange,
  valueText,
  children,
}: {
  id: string;
  value: number;
  min: number;
  max: number;
  step: Step;
  onChange: (v: number) => void;
  valueText: string;
  children?: ReactNode;
}) {
  return (
    <div className="relative h-7">
      <div className="pointer-events-none absolute inset-x-2 inset-y-0">{children}</div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={v}
        disabled={!(max > min)}
        aria-valuetext={valueText}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isFinite(n)) onChange(clamp(n, min, max));
        }}
        className={RANGE}
      />
    </div>
  );
}

const at = (v: number, min: number, max: number) => (max > min ? clamp((v - min) / (max - min), 0, 1) * 100 : 0);

/* ---------- the calculator ---------- */

export function Calculator({ c }: { c: unknown }) {
  const model = useMemo(() => parse(c), [c]);
  if (!model) return <p className="rounded-xl border border-dashed border-border px-3 py-6 text-center text-sm text-faint">measuring…</p>;
  return <CalculatorView m={model} />;
}

function CalculatorView({ m }: { m: Model }) {
  const uid = useId();
  const presets = useMemo(() => Object.fromEntries(PRESETS.map((p) => [p.id, presetValues(m, p.id)])) as Record<PresetId, Values>, [m]);
  const [vals, setVals] = useState<Values>(presets.base);
  const [f, setF] = useState(m.follow.base);
  const [open, setOpen] = useState(false);
  const [hot, setHot] = useState<number | null>(null);

  const e = economics(m, vals, f);
  const gain = Math.round(e.net) >= 0;
  const active = PRESETS.find((p) => KEYS.every((k) => Math.abs(vals[k] - presets[p.id][k]) < 1e-9))?.id ?? null;
  const self = useMemo(() => {
    if (!m.check) return null;
    const r = economics(m, presets.base, m.check.f);
    return {
      f: m.check.f,
      net: r.net,
      be: r.breakEven,
      netOk: m.check.net == null ? null : Math.abs(r.net - m.check.net) <= Math.max(1, Math.abs(m.check.net) * 1e-9),
      beOk: m.check.be == null ? null : Math.abs(r.breakEven - m.check.be) <= 1e-7,
      scriptNet: m.check.net,
      scriptBe: m.check.be,
    };
  }, [m, presets]);

  const pBe = at(e.breakEven, m.follow.min, m.follow.max);
  const changed = (a: Assumption) => Math.abs(vals[a.key] - a.base) > 1e-9;
  const followText = pct3(f);
  const beText = e.rawBreakEven <= 0 ? "0%" : e.rawBreakEven > 1 ? "over 100%" : pct3(e.breakEven);
  const beSub =
    e.rawBreakEven <= 0
      ? "pays for itself even if nobody stops"
      : e.rawBreakEven > 1
        ? "not reached even if every victim stops"
        : `1 in ${Math.round(1 / e.breakEven).toLocaleString("en-US")} paused victims`;

  const rows = [
    { label: "Scam money prevented", v: e.prevented },
    { label: e.analyst >= 0 ? "Analyst time saved by linking" : "Extra analyst time for linking", v: e.analyst },
    { label: "False pauses (customer time, support, lost fees)", v: -e.falsePauses },
    { label: "“Not sure” review cost", v: -e.reviews },
    { label: "Servers", v: -e.servers },
  ];
  const barMax = Math.max(...rows.map((r) => Math.abs(r.v)), Math.abs(e.net), 1e-9);

  const follow = (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={`${uid}-f`} className="text-sm font-medium">
          Follow rate
        </label>
        <span className="num font-mono text-2xl font-semibold tracking-tight">{followText}</span>
      </div>
      <p className="mt-0.5 text-xs text-muted-foreground">Share of paused scam victims who stop instead of sending. Ours is not measured yet (a pilot must), so you choose.</p>
      <div className="mt-2">
        <Range id={`${uid}-f`} value={f} min={m.follow.min} max={m.follow.max} step={m.follow.step} onChange={setF} valueText={`${followText} follow rate`}>
          <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 overflow-hidden rounded-full bg-muted">
            <span className="absolute inset-y-0 left-0 bg-risk/70" style={{ width: `${pBe}%` }} />
            <span className="absolute inset-y-0 right-0 bg-safe/45" style={{ left: `${pBe}%` }} />
          </div>
          {m.markers.map((mk, i) => (
            <span
              key={i}
              className={cn("absolute top-1/2 w-px -translate-x-1/2 -translate-y-1/2 transition-all", hot === i ? "h-6 bg-foreground" : "h-4 bg-foreground/60")}
              style={{ left: `${at(mk.value, m.follow.min, m.follow.max)}%` }}
            />
          ))}
        </Range>
      </div>
      <div className="flex items-center justify-between gap-3 font-mono text-[10px] text-faint">
        <span>{pct3(m.follow.min)}</span>
        <span className="inline-flex items-center gap-3">
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-3 rounded-full bg-risk/70" /> net loss
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-3 rounded-full bg-safe/45" /> net gain
          </span>
        </span>
        <span>{pct3(m.follow.max)}</span>
      </div>
      {(m.markers.length > 0 || Math.abs(f - m.follow.base) > 1e-12) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {m.markers.map((mk, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setF(mk.value)}
              onMouseEnter={() => setHot(i)}
              onMouseLeave={() => setHot(null)}
              onFocus={() => setHot(i)}
              onBlur={() => setHot(null)}
              title={`Set the follow rate to ${pct3(mk.value)}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-left text-[11px] leading-tight text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground"
            >
              <span className="h-3 w-px shrink-0 bg-foreground/60" aria-hidden="true" />
              <span className="num font-mono text-foreground">{pct3(mk.value)}</span> {mk.label}
            </button>
          ))}
          {Math.abs(f - m.follow.base) > 1e-12 && (
            <button
              type="button"
              onClick={() => setF(m.follow.base)}
              className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground"
            >
              <RotateCcw className="size-3" aria-hidden="true" /> back to {pct3(m.follow.base)}
            </button>
          )}
        </div>
      )}
    </div>
  );

  const outputs = (
    <div className="space-y-3">
      <div className={cn("rounded-2xl border p-4", gain ? "border-safe/40" : "border-risk/50")}>
        <p className="text-xs text-muted-foreground">Net benefit per 1 million transfers</p>
        <p className={cn("num mt-1 font-mono text-3xl font-semibold tracking-tight", gain ? "text-safe" : "text-risk")} aria-live="polite">
          {money(e.net)}
        </p>
        <p className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs">
          <span className={cn("inline-flex items-center gap-1 font-medium", gain ? "text-safe" : "text-risk")}>
            {gain ? <TrendingUp className="size-3.5" aria-hidden="true" /> : <TrendingDown className="size-3.5" aria-hidden="true" />}
            {gain ? "net gain" : "net loss"}
          </span>
          <span className="text-muted-foreground">at a {followText} follow rate</span>
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl border border-border p-4">
          <p className="num font-mono text-xl font-semibold tracking-tight">{beText}</p>
          <p className="mt-1 text-xs leading-tight">Break-even follow rate</p>
          <p className="mt-0.5 font-mono text-[11px] leading-tight text-faint">{beSub}</p>
        </div>
        <div className="rounded-2xl border border-border p-4">
          <p className="num font-mono text-xl font-semibold tracking-tight">{e.ratio == null ? "—" : `${e.ratio >= 100 ? Math.round(e.ratio) : e.ratio.toFixed(1)}×`}</p>
          <p className="mt-1 text-xs leading-tight">Benefit / cost</p>
          <p className="mt-0.5 font-mono text-[11px] leading-tight text-faint">what it saves ÷ what it costs</p>
        </div>
      </div>
      <div className="rounded-2xl border border-border p-4">
        <p className="text-xs text-muted-foreground">Where the net benefit comes from</p>
        <ul className="mt-3 space-y-2.5">
          {rows.map((r) => (
            <li key={r.label}>
              <div className="flex items-baseline justify-between gap-3 text-xs">
                <span className="leading-tight">{r.label}</span>
                <span className="num shrink-0 font-mono text-[11px]">{money(r.v, true)}</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-muted">
                <div className={cn("h-full rounded-full", r.v >= 0 ? "bg-foreground/70" : "bg-foreground/30")} style={{ width: `${(Math.abs(r.v) / barMax) * 100}%` }} />
              </div>
            </li>
          ))}
          <li className="border-t border-border pt-2.5">
            <div className="flex items-baseline justify-between gap-3 text-xs">
              <span className="font-medium">Net benefit</span>
              <span className={cn("num shrink-0 font-mono text-[11px] font-semibold", gain ? "text-safe" : "text-risk")}>{money(e.net, true)}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-muted">
              <div className={cn("h-full rounded-full", gain ? "bg-safe" : "bg-risk")} style={{ width: `${(Math.abs(e.net) / barMax) * 100}%` }} />
            </div>
          </li>
        </ul>
      </div>
    </div>
  );

  const assumptions = (
    <div className="@container space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="label-mono">Assumptions</p>
        {active === null && <span className="font-mono text-[11px] text-faint">your own mix</span>}
      </div>
      <div role="group" aria-label="Assumption presets" className="grid w-full grid-cols-3 gap-1 rounded-full border border-border p-1 sm:inline-grid sm:w-auto">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            aria-pressed={active === p.id}
            onClick={() => setVals(presets[p.id])}
            className={cn(
              "h-9 rounded-full px-2 text-[11px] leading-tight transition-colors sm:px-3.5 sm:text-xs",
              active === p.id ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={`${uid}-grid`}
        className="flex w-full items-center justify-between rounded-xl border border-dashed border-border px-4 py-3 text-left text-sm hover:border-foreground/40 sm:hidden"
      >
        <span>Change the assumptions ({m.assumptions.length})</span>
        <ChevronDown className={cn("size-4 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden="true" />
      </button>
      <div id={`${uid}-grid`} className={cn("space-y-3 sm:block", !open && "hidden")}>
        <p className="text-[11px] text-faint">Each slider spans our stated low–high range; the notch is our base value.</p>
        <div className="grid gap-x-6 gap-y-4 @lg:grid-cols-2 @4xl:grid-cols-3">
          {m.assumptions.map((a) => {
            const v = vals[a.key];
            const pBase = at(a.base, a.lo, a.hi);
            const pV = at(v, a.lo, a.hi);
            const pessLow = a.pess === a.lo && a.pess !== a.hi;
            return (
              <div key={a.key}>
                <div className="flex items-baseline justify-between gap-3">
                  <label htmlFor={`${uid}-${a.key}`} className="text-xs leading-snug">
                    {a.label}
                  </label>
                  <span className={cn("num shrink-0 font-mono text-xs", changed(a) ? "font-semibold text-foreground" : "text-muted-foreground")}>{value(v, a.unit)}</span>
                </div>
                <Range
                  id={`${uid}-${a.key}`}
                  value={v}
                  min={a.lo}
                  max={a.hi}
                  step={a.step}
                  onChange={(n) => setVals((cur) => ({ ...cur, [a.key]: n }))}
                  valueText={value(v, a.unit)}
                >
                  <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-muted">
                    <span className="absolute inset-y-0 rounded-full bg-foreground/40" style={{ left: `${Math.min(pBase, pV)}%`, width: `${Math.abs(pV - pBase)}%` }} />
                  </div>
                  <span className="absolute top-1/2 h-3 w-px -translate-x-1/2 -translate-y-1/2 bg-foreground/60" style={{ left: `${pBase}%` }} title={`base ${value(a.base, a.unit)}`} />
                </Range>
                <div className="flex justify-between gap-2 font-mono text-[10px] text-faint">
                  <span>
                    {value(a.lo, a.unit)}
                    {pessLow && " · pessimistic"}
                  </span>
                  <span>
                    {!pessLow && "pessimistic · "}
                    {value(a.hi, a.unit)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  return (
    <div className="@container">
      <div className="grid gap-6 @3xl:grid-cols-[minmax(0,1fr)_minmax(0,20rem)] @3xl:gap-x-8">
        <div className="@3xl:col-start-1 @3xl:row-start-1">{follow}</div>
        <div className="@3xl:col-start-2 @3xl:row-span-2 @3xl:row-start-1">
          <div className="@3xl:sticky @3xl:top-24">{outputs}</div>
        </div>
        <div className="@3xl:col-start-1 @3xl:row-start-2">{assumptions}</div>
      </div>
      {self && (
        <p className={cn("mt-5 flex gap-1.5 text-[11px] leading-snug", self.netOk === false || self.beOk === false ? "text-caution" : "text-faint")}>
          {self.netOk === false || self.beOk === false ? (
            <AlertTriangle className="mt-px size-3.5 shrink-0" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="mt-px size-3.5 shrink-0" aria-hidden="true" />
          )}
          <span>
            Same arithmetic as <span className="font-mono">economics()</span> in scripts/phase2/business_case.py.{" "}
            {self.netOk === false || self.beOk === false ? (
              <>
                Self-check failed: at our base and a {pct3(self.f)} follow rate this page gives {money(self.net)} and {pct3(self.be)}; the script wrote{" "}
                {self.scriptNet == null ? "no net benefit" : money(self.scriptNet)} and {self.scriptBe == null ? "no break-even" : pct3(self.scriptBe)}.
              </>
            ) : (
              <>
                Self-check: at our base and a {pct3(self.f)} follow rate this page gives {money(self.net)}
                {self.beOk ? <> and a break-even of {pct3(self.be)}</> : null}, the same as the script.
              </>
            )}
          </span>
        </p>
      )}
    </div>
  );
}
