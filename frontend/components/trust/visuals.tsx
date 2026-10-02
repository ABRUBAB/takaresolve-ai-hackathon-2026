"use client";

import {
  Banknote,
  CalendarClock,
  Clock,
  KeyRound,
  LogOut,
  Moon,
  Repeat,
  Smartphone,
  Sparkles,
  UserPlus,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { pct } from "@/lib/format";
import type { Reason } from "@/lib/types";
import { cn } from "@/lib/utils";

/** A 270° gauge. Green → amber → red track, a needle-free fill and the number in the middle. */
export function RiskDial({
  p,
  size = 220,
  label = "chance this is a scam",
  tone,
  className,
  children,
}: {
  p: number;
  size?: number;
  label?: string;
  tone?: "risk" | "caution" | "safe" | "unsure";
  className?: string;
  children?: React.ReactNode;
}) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const arc = 0.75 * c;
  const v = Math.max(0.02, Math.min(1, p));
  const t = tone ?? (p >= 0.5 ? "risk" : p >= 0.2 ? "caution" : "safe");
  const stroke = { risk: "stroke-risk", caution: "stroke-caution", safe: "stroke-safe", unsure: "stroke-unsure" }[t];
  return (
    <div className={cn("relative grid place-items-center", className)} style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-[225deg]" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="none" className="stroke-muted" strokeWidth="7" strokeLinecap="round" strokeDasharray={`${arc} ${c}`} />
        <motion.circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          className={cn(stroke, t === "unsure" && "[stroke-dasharray:2_3]")}
          strokeWidth="7"
          strokeLinecap="round"
          initial={{ strokeDasharray: `0 ${c}` }}
          animate={{ strokeDasharray: `${arc * v} ${c}` }}
          transition={{ duration: 1.1, ease: [0.2, 0.8, 0.2, 1] }}
        />
      </svg>
      <div className="relative text-center">
        {children}
        <p className="num font-mono text-[clamp(1.6rem,4vw,2.4rem)] font-semibold leading-none tracking-tight">{pct(p)}</p>
        <p className="mt-1 text-[11px] text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

const FEATURE: Record<string, { icon: LucideIcon; value: (v: number) => string; label: string }> = {
  recipient_sender_days_7d: { icon: Users, value: (v) => `${Math.round(v)}`, label: "people paid them this week" },
  recipient_in_count_7d: { icon: Users, value: (v) => `${Math.round(v)}`, label: "payments in this week" },
  recipient_out_in_ratio_7d: { icon: LogOut, value: (v) => pct(v), label: "of money moves on" },
  recipient_age_days: { icon: CalendarClock, value: (v) => `${Math.round(v)} d`, label: "receiver wallet age" },
  recipient_cashout_count_7d: { icon: Banknote, value: (v) => `${Math.round(v)}`, label: "cash-outs this week" },
  recipient_in_today_before: { icon: Repeat, value: (v) => `${Math.round(v)}`, label: "payments in today" },
  amount_to_balance: { icon: Wallet, value: (v) => pct(v), label: "of the balance" },
  amount_log: { icon: Banknote, value: () => "unusual", label: "amount" },
  amount_z_30d: { icon: Banknote, value: (v) => `${v.toFixed(1)}×`, label: "above usual amount" },
  first_time_pair: { icon: UserPlus, value: () => "new", label: "first time to them" },
  pin_reset_72h: { icon: KeyRound, value: () => "PIN", label: "reset in 3 days" },
  device_change_72h: { icon: Smartphone, value: () => "new", label: "phone in 3 days" },
  cash_in_gap_min: { icon: Clock, value: (v) => `${Math.round(v)} min`, label: "after a cash-in" },
  hour: { icon: Moon, value: (v) => `${String(Math.floor(v)).padStart(2, "0")}:00`, label: "time of day" },
  is_night: { icon: Moon, value: () => "night", label: "late transfer" },
  sender_out_count_7d: { icon: Repeat, value: (v) => `${Math.round(v)}`, label: "transfers you sent this week" },
  sender_tenure_days: { icon: CalendarClock, value: (v) => `${Math.round(v)} d`, label: "your wallet age" },
};

/** Model reasons as icon tiles; tap a tile to read the full sentence (EN or BN). */
export function ReasonTiles({ reasons, lang = "en", className }: { reasons: Reason[]; lang?: "en" | "bn"; className?: string }) {
  const [open, setOpen] = useState<string | null>(null);
  const picked = reasons.find((r) => r.feature === open);
  return (
    <div className={cn("space-y-2", className)}>
      <div className="grid grid-cols-3 gap-2">
        {reasons.slice(0, 3).map((r, i) => {
          const f = FEATURE[r.feature] ?? { icon: Sparkles, value: () => "", label: r.feature.replace(/_/g, " ") };
          const Icon = f.icon;
          const on = open === r.feature;
          return (
            <motion.button
              key={r.feature}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 + i * 0.08 }}
              onClick={() => setOpen(on ? null : r.feature)}
              aria-expanded={on}
              className={cn(
                "flex min-h-24 flex-col items-center justify-center gap-1 rounded-2xl border px-1 py-3 text-center transition-colors",
                on ? "border-foreground/50 bg-muted" : "border-border bg-background/40 hover:border-foreground/30",
              )}
            >
              <Icon className="size-5 text-risk" aria-hidden="true" />
              <span className="num font-mono text-sm font-semibold">{f.value(r.value)}</span>
              <span className="text-[10.5px] leading-tight text-muted-foreground">{f.label}</span>
            </motion.button>
          );
        })}
      </div>
      {picked && (
        <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className={cn("rounded-xl bg-muted/60 px-3 py-2 text-sm", lang === "bn" && "bn")}>
          {lang === "bn" ? picked.text_bn : picked.text_en}
        </motion.p>
      )}
    </div>
  );
}

/** A small "waffle" of dots: n of total filled. Good for "377 alerts → 197 cases" style facts. */
export function DotWaffle({ filled, total, cols = 20, className }: { filled: number; total: number; cols?: number; className?: string }) {
  return (
    <div className={cn("grid gap-1", className)} style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }} aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <motion.span
          key={i}
          className={cn("aspect-square rounded-full", i < filled ? "bg-volt-ink dark:bg-volt" : "bg-muted")}
          initial={{ scale: 0 }}
          whileInView={{ scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: (i % cols) * 0.012 + Math.floor(i / cols) * 0.03, type: "spring", stiffness: 300, damping: 18 }}
        />
      ))}
    </div>
  );
}
