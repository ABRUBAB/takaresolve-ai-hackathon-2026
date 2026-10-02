import { AlertOctagon, Bot, CircleHelp, FileCog, FlaskConical, ShieldCheck, Sparkles, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type OutputType = "model" | "rule" | "generated" | "assumption";

const OUTPUT: Record<OutputType, { label: string; icon: ReactNode; cls: string }> = {
  model: { label: "Model estimate", icon: <Bot className="size-3" />, cls: "text-model border-model/40" },
  rule: { label: "Business rule", icon: <FileCog className="size-3" />, cls: "text-rule border-rule/40" },
  generated: { label: "Generated wording", icon: <Sparkles className="size-3" />, cls: "text-generated border-generated/40" },
  assumption: { label: "Assumption · synthetic", icon: <FlaskConical className="size-3" />, cls: "text-muted-foreground border-border" },
};

/** Every AI output is labelled with what kind of thing it is (Guideline §14: transparency). */
export function OutputChip({ type, className, children }: { type: OutputType; className?: string; children?: ReactNode }) {
  const o = OUTPUT[type];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em]", o.cls, className)}>
      {o.icon}
      {children ?? o.label}
    </span>
  );
}

export type RiskState = "low" | "medium" | "high" | "unsure" | "basic";

const RISK: Record<RiskState, { label: string; icon: ReactNode; cls: string }> = {
  low: { label: "Low risk", icon: <ShieldCheck className="size-3.5" />, cls: "text-safe border-safe/40 bg-safe/10" },
  medium: { label: "Some warning signs", icon: <TriangleAlert className="size-3.5" />, cls: "text-caution border-caution/40 bg-caution/10" },
  high: { label: "High scam risk", icon: <AlertOctagon className="size-3.5" />, cls: "text-risk border-risk/40 bg-risk/10" },
  unsure: { label: "Not sure", icon: <CircleHelp className="size-3.5" />, cls: "text-unsure border-dashed border-unsure/60 bg-transparent" },
  basic: { label: "Basic check only", icon: <TriangleAlert className="size-3.5" />, cls: "text-muted-foreground border-border" },
};

/** Risk is never shown by colour alone: icon + word + colour. "Not sure" is calm grey with a dashed border. */
export function RiskBadge({ state, label, className }: { state: RiskState; label?: string; className?: string }) {
  const r = RISK[state];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium", r.cls, className)}>
      {r.icon}
      {label ?? r.label}
    </span>
  );
}

export function riskStateOf(level?: string, uncertainty?: string): RiskState {
  if (uncertainty === "unsure") return "unsure";
  if (level === "high") return "high";
  if (level === "medium") return "medium";
  if (level === "low") return "low";
  return "basic";
}

export function SyntheticBadge({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border border-dashed border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground", className)}>
      <FlaskConical className="size-3" /> Synthetic demo data
    </span>
  );
}
