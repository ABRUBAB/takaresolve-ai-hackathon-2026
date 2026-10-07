"use client";

import { CheckCircle2, CircleDashed } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Phase 2 evidence files (frontend/public/data/phase2/*.json, documented in the README there).
 * Every file has the same shape, so the page can render any of them; values that are null show as "measuring…".
 */
export type Unit = "pct" | "pct1" | "num" | "num1" | "num3" | "bdt" | "ms" | "s" | "x" | "text";
export type Headline = { label: string; value: number | string | null; format?: Unit; sub?: string };
export type Series = { name: string; values: (number | null)[] };
export type Chart =
  | { kind: "bars"; unit?: Unit; x: string[]; series: Series[]; higher_is_better?: boolean }
  | { kind: "line"; unit?: Unit; x: (number | string)[]; x_label?: string; series: Series[] }
  | { kind: "table"; columns: string[]; rows: (string | number | null)[][]; units?: (Unit | null)[] };
export type EvidenceSection = { id: string; title: string; lead?: string; chart?: Chart | null; takeaway?: string };
export type EvidenceFile = {
  status: "pending" | "measured";
  title: string;
  updated_at?: string | null;
  source?: string;
  summary?: string;
  headline?: Headline[];
  sections?: EvidenceSection[];
  caveats?: string[];
};

const isTbd = (v: unknown) => v == null || (typeof v === "string" && /^\s*TBD/i.test(v));

export function fmt(v: unknown, unit: Unit = "num"): string {
  if (isTbd(v)) return "measuring…";
  if (typeof v === "string") return v;
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  switch (unit) {
    case "pct":
      return `${Math.round(v * 100)}%`;
    case "pct1":
      return `${(v * 100).toFixed(1)}%`;
    case "num1":
      return v.toLocaleString("en-US", { maximumFractionDigits: 1 });
    case "num3":
      return v.toFixed(3);
    case "bdt":
      return `Tk ${Math.round(v).toLocaleString("en-US")}`;
    case "ms":
      return `${v.toLocaleString("en-US", { maximumFractionDigits: 0 })} ms`;
    case "s":
      return `${v.toLocaleString("en-US", { maximumFractionDigits: 1 })} s`;
    case "x":
      return `${v.toFixed(1)}×`;
    default:
      return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
}

export function StatusBadge({ measured }: { measured: boolean }) {
  return measured ? (
    <span className="inline-flex items-center gap-1 rounded-full border border-volt-ink/50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-volt-ink dark:border-volt/40 dark:text-volt">
      <CheckCircle2 className="size-3" /> measured
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-faint">
      <CircleDashed className="size-3" /> pending · measuring…
    </span>
  );
}

export function HeadlineTiles({ items }: { items: Headline[] }) {
  if (!items.length) return null;
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((h, i) => {
        const pending = isTbd(h.value);
        return (
          <div key={i} className={cn("rounded-2xl border p-4", pending ? "border-dashed border-border" : "border-border")}>
            <p className={cn("num font-mono font-semibold tracking-tight", pending ? "text-lg text-faint" : "text-3xl")}>{fmt(h.value, h.format)}</p>
            <p className="mt-1 text-sm">{isTbd(h.label) ? "Metric to be named" : h.label}</p>
            {h.sub && !isTbd(h.sub) && <p className="mt-0.5 font-mono text-[11px] text-faint">{h.sub}</p>}
          </div>
        );
      })}
    </div>
  );
}

const SERIES_CLASS = ["bg-foreground/70", "bg-volt-ink dark:bg-volt", "bg-foreground/35", "bg-model", "bg-rule"];
const SERIES_STROKE = ["var(--foreground)", "var(--volt-ink)", "var(--muted-foreground)", "var(--chip-model)", "var(--chip-rule)"];

function Legend({ series }: { series: Series[] }) {
  if (series.length < 2) return null;
  return (
    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
      {series.map((s, i) => (
        <span key={s.name} className="inline-flex items-center gap-1.5">
          <span className={cn("size-2.5 rounded-sm", SERIES_CLASS[i % SERIES_CLASS.length])} /> {s.name}
        </span>
      ))}
    </div>
  );
}

function BarsChart({ c }: { c: Extract<Chart, { kind: "bars" }> }) {
  const all = c.series.flatMap((s) => s.values).filter((v): v is number => typeof v === "number");
  const max = Math.max(...all.map(Math.abs), c.unit === "pct" || c.unit === "pct1" ? 1 : 0, 1e-9);
  return (
    <div className="space-y-3">
      <Legend series={c.series} />
      {c.x.map((label, xi) => (
        <div key={label}>
          <p className="text-xs leading-tight">{label}</p>
          <div className="mt-1.5 space-y-1">
            {c.series.map((s, si) => {
              const v = s.values[xi];
              return (
                <div key={s.name} className="grid grid-cols-[1fr_5.5rem] items-center gap-2">
                  <div className="h-2.5 rounded-full bg-muted">
                    {typeof v === "number" && (
                      <div className={cn("h-full rounded-full", SERIES_CLASS[si % SERIES_CLASS.length])} style={{ width: `${(Math.abs(v) / max) * 100}%` }} />
                    )}
                  </div>
                  <span className={cn("num text-right font-mono text-[11px]", v == null && "text-faint")}>{fmt(v, c.unit)}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function LineChart({ c }: { c: Extract<Chart, { kind: "line" }> }) {
  const W = 420;
  const H = 220;
  const P = { l: 58, r: 12, t: 12, b: 40 };
  const vals = c.series.flatMap((s) => s.values).filter((v): v is number => typeof v === "number");
  if (!vals.length) return <p className="text-sm text-faint">measuring…</p>;
  const lo = Math.min(0, ...vals);
  const hi = Math.max(...vals) || 1;
  const px = (i: number) => P.l + (c.x.length > 1 ? (i / (c.x.length - 1)) * (W - P.l - P.r) : (W - P.l - P.r) / 2);
  const py = (v: number) => H - P.b - ((v - lo) / (hi - lo || 1)) * (H - P.t - P.b);
  const ticks = [lo, (lo + hi) / 2, hi];
  return (
    <div className="space-y-2">
      <Legend series={c.series} />
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Line chart">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={P.l} x2={W - P.r} y1={py(t)} y2={py(t)} stroke="var(--border)" />
            <text x={P.l - 6} y={py(t) + 3} textAnchor="end" fontSize="12" fill="var(--faint)" fontFamily="var(--font-geist-mono)">
              {fmt(t, c.unit)}
            </text>
          </g>
        ))}
        {c.x.map((x, i) => (
          <text key={i} x={px(i)} y={H - P.b + 18} textAnchor="middle" fontSize="12" fill="var(--faint)" fontFamily="var(--font-geist-mono)">
            {x}
          </text>
        ))}
        {c.x_label && (
          <text x={(W + P.l) / 2} y={H - 4} textAnchor="middle" fontSize="12" fill="var(--muted-foreground)">
            {c.x_label}
          </text>
        )}
        {c.series.map((s, si) => {
          const pts = s.values.map((v, i) => (typeof v === "number" ? [px(i), py(v)] : null)).filter((p): p is number[] => !!p);
          const stroke = SERIES_STROKE[si % SERIES_STROKE.length];
          return (
            <g key={s.name}>
              <polyline points={pts.map((p) => p.join(",")).join(" ")} fill="none" stroke={stroke} strokeWidth="2" />
              {pts.map((p, i) => (
                <circle key={i} cx={p[0]} cy={p[1]} r="3" fill={stroke} />
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function TableChart({ c }: { c: Extract<Chart, { kind: "table" }> }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[320px] text-sm">
        <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
          <tr>
            {c.columns.map((h, i) => (
              <th key={i} className={cn("px-3 py-2 font-normal", i > 0 && "text-right")}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {c.rows.map((r, ri) => (
            <tr key={ri}>
              {r.map((v, i) => (
                <td key={i} className={cn("px-3 py-2", i > 0 && "num text-right font-mono text-xs", isTbd(v) && "text-faint")}>
                  {i === 0 && typeof v === "string" && !isTbd(v) ? v : fmt(v, c.units?.[i] ?? (typeof v === "number" ? "num" : "text"))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChartView({ chart }: { chart?: Chart | null }) {
  if (!chart) return <p className="rounded-xl border border-dashed border-border px-3 py-6 text-center text-sm text-faint">measuring…</p>;
  if (chart.kind === "bars") return <BarsChart c={chart} />;
  if (chart.kind === "line") return <LineChart c={chart} />;
  if (chart.kind === "table") return <TableChart c={chart} />;
  return null;
}

export function SectionView({ s, measured }: { s: EvidenceSection; measured: boolean }) {
  return (
    <div className="rounded-2xl border border-border p-5">
      <p className="font-medium">{isTbd(s.title) ? "Evidence" : s.title}</p>
      {s.lead && !isTbd(s.lead) && <p className="mt-1 text-sm text-muted-foreground">{s.lead}</p>}
      <div className="mt-4">{measured ? <ChartView chart={s.chart} /> : <ChartView chart={null} />}</div>
      {measured && s.takeaway && !isTbd(s.takeaway) && <p className="mt-4 border-t border-border pt-3 text-sm">{s.takeaway}</p>}
    </div>
  );
}

export function EvidenceBlock({ file, sectionId, name, extra }: { file: EvidenceFile | null; sectionId?: string; name: string; extra?: ReactNode }) {
  const measured = file?.status === "measured";
  const sections = (file?.sections ?? []).filter((s) => !sectionId || s.id === sectionId);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-muted-foreground">
          {name}.json{sectionId ? ` · ${sectionId}` : ""}
        </span>
        <StatusBadge measured={measured} />
        {measured && file?.updated_at && <span className="font-mono text-[11px] text-faint">updated {file.updated_at.slice(0, 16).replace("T", " ")}</span>}
      </div>
      {!file ? (
        <p className="rounded-xl border border-dashed border-border px-3 py-6 text-center text-sm text-faint">measuring… (no results file yet)</p>
      ) : (
        <>
          {!sectionId && file.summary && !isTbd(file.summary) && measured && <p className="text-sm text-muted-foreground">{file.summary}</p>}
          {!sectionId && file.headline && <HeadlineTiles items={measured ? file.headline : file.headline.map((h) => ({ ...h, value: null }))} />}
          {sections.length > 0 ? (
            <div className="grid gap-3 lg:grid-cols-2">
              {sections.map((s) => (
                <SectionView key={s.id} s={s} measured={measured} />
              ))}
            </div>
          ) : (
            sectionId && <p className="rounded-xl border border-dashed border-border px-3 py-6 text-center text-sm text-faint">measuring…</p>
          )}
          {measured && file.caveats && file.caveats.filter((c) => !isTbd(c)).length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
              {file.caveats.filter((c) => !isTbd(c)).map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          )}
          {measured && file.source && <p className="font-mono text-[11px] text-faint">Source: {file.source}</p>}
        </>
      )}
      {extra}
    </div>
  );
}
