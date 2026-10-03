"use client";

import { ChevronDown, ScanSearch } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * "Behind the screen": the raw model outputs a judge or analyst can verify, next to what the user sees.
 * Closed by default so the page stays clean; `summary` shows a few key facts while it is closed.
 */
export function Inspector({
  title = "Behind the screen",
  children,
  className,
  summary,
  defaultOpen = false,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
  summary?: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <aside className={cn("overflow-hidden rounded-3xl border border-border bg-card", className)} aria-label={title}>
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full items-center gap-2 px-5 py-4 text-left hover:bg-muted/40">
        <ScanSearch className="size-4 text-muted-foreground" aria-hidden="true" />
        <span className="text-sm font-medium">{title}</span>
        <span className="label-mono ml-2 hidden sm:inline">for reviewers</span>
        <span className="ml-auto inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
          {open ? "Hide the analysis" : "Show the analysis"}
          <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />
        </span>
      </button>
      {!open && summary && <div className="border-t border-border px-5 py-4">{summary}</div>}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
            className="overflow-hidden"
          >
            <div className="space-y-6 border-t border-border p-5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </aside>
  );
}

export function InspectorSection({ title, chip, children }: { title: string; chip?: ReactNode; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="label-mono">{title}</h3>
        {chip}
      </div>
      {children}
    </section>
  );
}

export function KV({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="divide-y divide-border rounded-2xl border border-border text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-start justify-between gap-4 px-3 py-2">
          <dt className="text-muted-foreground">{k}</dt>
          <dd className="num text-right font-mono text-[13px]">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Small key facts shown while the inspector is closed. */
export function SummaryChips({ items }: { items: [string, ReactNode][] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map(([k, v]) => (
        <span key={k} className="inline-flex items-baseline gap-1.5 rounded-full bg-muted/70 px-3 py-1 text-xs">
          <span className="text-muted-foreground">{k}</span>
          <span className="num font-mono font-medium">{v}</span>
        </span>
      ))}
    </div>
  );
}

export function TraceFooter({ trace, model, data }: { trace?: string; model?: string; data?: string }) {
  if (!trace) return null;
  return (
    <p className="border-t border-border pt-4 font-mono text-[11px] leading-relaxed text-faint">
      trace {trace}
      <br />
      model {model || "—"} · data {data || "—"}
    </p>
  );
}

export function EmptyInspector({ text }: { text: string }) {
  return <p className="rounded-2xl border border-dashed border-border p-4 text-sm text-muted-foreground">{text}</p>;
}
