"use client";

import { motion } from "motion/react";
import { Fragment } from "react";
import { pct } from "@/lib/format";
import type { Reason } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Probability bar with the frozen alert thresholds marked, so the number is read against the rule that uses it. */
export function ProbabilityMeter({
  p,
  marks = [],
  label = "Calibrated chance",
  className,
}: {
  p: number;
  marks?: { at: number; label: string }[];
  label?: string;
  className?: string;
}) {
  const tone = p >= 0.5 ? "bg-risk" : p >= 0.2 ? "bg-caution" : "bg-safe";
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="num font-mono text-2xl font-semibold tracking-tight">{pct(p)}</span>
      </div>
      <div className="relative h-2 rounded-full bg-muted">
        <motion.div
          className={cn("absolute inset-y-0 left-0 rounded-full", tone)}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(1.5, Math.min(100, p * 100))}%` }}
          transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}
        />
        {marks.map((m) => (
          <span
            key={m.label}
            className="absolute -top-1 h-4 w-px bg-foreground/50"
            style={{ left: `${Math.min(99.5, m.at * 100)}%` }}
            title={m.label}
            aria-hidden="true"
          />
        ))}
      </div>
      {marks.length > 0 && (
        <p className="text-xs text-faint">
          {marks.map((m, i) => (
            <Fragment key={m.label}>
              {i > 0 && " · "}
              {m.label} at {pct(m.at, 1)}
            </Fragment>
          ))}
        </p>
      )}
    </div>
  );
}

/** Exact TreeSHAP contributions turned into plain-language reasons; the bar length is the reason's share of the push. */
export function ReasonList({ reasons, lang = "en", className }: { reasons: Reason[]; lang?: "en" | "bn"; className?: string }) {
  const max = Math.max(...reasons.map((r) => Math.abs(r.contribution)), 1e-6);
  return (
    <ol className={cn("space-y-3", className)}>
      {reasons.map((r, i) => (
        <li key={r.feature} className="space-y-1.5">
          <div className="flex items-start gap-3">
            <span className="num mt-0.5 font-mono text-[11px] text-faint">R{i + 1}</span>
            <p className={cn("text-sm leading-snug", lang === "bn" && "bn")}>{lang === "bn" ? r.text_bn : r.text_en}</p>
          </div>
          <div className="ml-7 h-1 rounded-full bg-muted">
            <motion.div
              className={cn("h-full rounded-full", r.contribution >= 0 ? "bg-foreground/80" : "bg-safe")}
              initial={{ width: 0 }}
              animate={{ width: `${(Math.abs(r.contribution) / max) * 100}%` }}
              transition={{ duration: 0.8, delay: 0.1 + i * 0.08, ease: [0.2, 0.8, 0.2, 1] }}
            />
          </div>
        </li>
      ))}
    </ol>
  );
}

/** The scam message with the phrases that moved the verdict most (occlusion: remove the phrase, the score drops). */
export function HighlightedText({ text, highlights, className }: { text: string; highlights: { phrase: string }[]; className?: string }) {
  const phrases = highlights.map((h) => h.phrase).filter(Boolean);
  if (!phrases.length) return <p className={className}>{text}</p>;
  const escaped = phrases.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "g"));
  return (
    <p className={className}>
      {parts.map((part, i) =>
        phrases.includes(part) ? (
          <mark key={i} className="rounded bg-volt/80 px-0.5 text-black">
            {part}
          </mark>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </p>
  );
}

const UNSURE: Record<string, string> = {
  input_unlike_training_data: "This situation looks unlike what the AI learned from.",
  conformal_set_has_both_labels: "The evidence points both ways: both answers are still plausible.",
};

export const unsureText = (code: string) => UNSURE[code] ?? code.replace(/_/g, " ");

const ACTIONS: Record<string, { en: string; bn: string }> = {
  wait_10_min: { en: "Wait 10 minutes", bn: "১০ মিনিট অপেক্ষা করুন" },
  verify_number: { en: "Verify the number", bn: "নম্বরটি যাচাই করুন" },
  ask_trusted_contact: { en: "Ask someone I trust", bn: "বিশ্বস্ত কাউকে জিজ্ঞেস করুন" },
  continue_anyway: { en: "Continue if sure", bn: "নিশ্চিত হলে এগিয়ে যান" },
  soft_warning: { en: "Read the warning", bn: "সতর্কবার্তা পড়ুন" },
  proceed: { en: "Send", bn: "পাঠান" },
};

export const actionText = (code: string, lang: "en" | "bn" = "en") => ACTIONS[code]?.[lang] ?? code.replace(/_/g, " ");
