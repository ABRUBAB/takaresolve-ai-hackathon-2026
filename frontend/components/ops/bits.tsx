import { AlertOctagon, Clock, ShieldQuestion } from "lucide-react";
import { hoursText } from "@/lib/format";
import type { Deadline, QrState } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Remaining time on a dispute deadline. Colour + icon + words, never colour alone. */
export function DeadlineBar({ d, compact = false }: { d: Deadline | null; compact?: boolean }) {
  if (!d) return <span className="text-xs text-faint">No open deadline</span>;
  const tone = d.status === "breached" ? "bg-risk" : d.status === "urgent" ? "bg-caution" : "bg-foreground/50";
  const frac = Math.max(0.02, Math.min(1, d.remaining_fraction));
  return (
    <div className={cn("space-y-1", compact ? "min-w-36" : "")}>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className={cn("truncate", compact && "max-w-40")}>{d.label}</span>
        <span className={cn("num flex shrink-0 items-center gap-1 font-mono", d.status === "urgent" && "text-caution", d.status === "breached" && "text-risk")}>
          {d.status === "breached" ? <AlertOctagon className="size-3" /> : <Clock className="size-3" />}
          {hoursText(d.remaining_hours)}
        </span>
      </div>
      <div className="h-1 rounded-full bg-muted">
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${frac * 100}%` }} />
      </div>
    </div>
  );
}

const STATUS: Record<string, string> = {
  open: "Open",
  in_review: "In review",
  evidence_requested: "Evidence requested",
  hold_approved: "Hold approved",
  escalated: "Escalated",
  closed_no_action: "Dismissed",
  closed: "Closed",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-2 py-0.5 text-[11px]",
        status === "open" ? "border-foreground/40" : status.startsWith("closed") ? "border-border text-faint" : "border-volt-ink text-volt-ink dark:border-volt dark:text-volt",
      )}
    >
      {STATUS[status] ?? status}
    </span>
  );
}

const QR: Record<QrState, { label: string; cls: string }> = {
  red: { label: "Review now", cls: "border-risk/50 bg-risk/10 text-risk" },
  amber: { label: "Watch", cls: "border-caution/50 bg-caution/10 text-caution" },
  grey_review: { label: "Not sure · person checks", cls: "border-dashed border-unsure/60 text-unsure" },
  green: { label: "Normal", cls: "border-safe/40 text-safe" },
};

export function QrBadge({ state }: { state: QrState }) {
  const q = QR[state] ?? QR.green;
  return (
    <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium", q.cls)}>
      {state === "grey_review" && <ShieldQuestion className="size-3" />}
      {q.label}
    </span>
  );
}
