"use client";

import { ScanSearch } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** "Behind the screen": the raw model outputs a judge or analyst can verify, next to what the user sees. */
export function Inspector({ title = "Behind the screen", children, className }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <aside className={cn("rounded-3xl border border-border bg-card", className)} aria-label={title}>
      <div className="flex items-center gap-2 border-b border-border px-5 py-3">
        <ScanSearch className="size-4 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm font-medium">{title}</p>
        <span className="label-mono ml-auto">for reviewers</span>
      </div>
      <div className="space-y-6 p-5">{children}</div>
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
