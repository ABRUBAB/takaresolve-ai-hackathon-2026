"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";
import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

const ACTS = [
  {
    who: "Rubab · customer",
    time: "19:30",
    title: "A prize message asks for a Tk 3,000 fee.",
    body: "Rubab cashed in 25 minutes ago and is about to send it. UVERA pauses before the money moves, explains why in Bangla, and leaves the decision to Rubab. Nothing is blocked.",
    ais: ["AI-1 Pause Check", "AI-2 Scam Text", "AI-7 Brief"],
    href: "/customer/send?scenario=golden_prize_scam",
    cta: "Try Rubab's transfer",
  },
  {
    who: "Tanvir · agent",
    time: "Monday",
    title: "How much cash will the week ask for?",
    body: "Tanvir sees a 7-day forecast with an honest range, and how much cash to hold for a 90%-safe day — not a false yes/no alarm.",
    ais: ["AI-4 Liquidity", "AI-5 QR Shield (zone)"],
    href: "/agent",
    cta: "Open Tanvir's week",
  },
  {
    who: "Abdur Rahman · operations",
    time: "Next morning",
    title: "One hundred alerts become one case.",
    body: "Transfers, mule wallets and QR shops that share money paths are joined into one case with evidence, a dispute deadline clock and a grounded brief. A person decides every hold.",
    ais: ["AI-6 Case Linker", "AI-7 Brief", "AI-5 QR Shield"],
    href: "/ops",
    cta: "Open the case queue",
  },
];

function PhoneVisual() {
  return (
    <div className="relative mx-auto w-[280px] rounded-[2.5rem] border border-border bg-background p-3 shadow-2xl shadow-black/30">
      <div className="rounded-[2rem] border border-border bg-card px-5 pb-6 pt-8">
        <div className="mx-auto mb-6 h-1 w-16 rounded-full bg-muted" />
        <div className="relative mx-auto grid size-24 place-items-center">
          <motion.span
            className="absolute inset-0 rounded-full border-2 border-volt"
            initial={{ scale: 0.4, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}
          />
          <span className="flex gap-2">
            <span className="h-9 w-2.5 rounded-sm bg-foreground" />
            <span className="h-9 w-2.5 rounded-sm bg-volt" />
          </span>
        </div>
        <p className="bn mt-5 text-center text-lg font-semibold">আপনার নিরাপত্তার জন্য থামানো হয়েছে</p>
        <p className="mt-1 text-center text-xs text-muted-foreground">Paused for your safety · Tk 3,000</p>
        <ul className="mt-5 space-y-2 text-[13px]">
          {["Many people sent money to this receiver this week", "Money sent here leaves quickly", "The receiving wallet is 12 days old"].map((t, i) => (
            <motion.li
              key={t}
              className="flex gap-2"
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 + i * 0.12 }}
            >
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-risk" />
              {t}
            </motion.li>
          ))}
        </ul>
        <div className="mt-6 space-y-2">
          <div className="rounded-full bg-foreground py-2.5 text-center text-sm font-medium text-background">Wait 10 minutes</div>
          <div className="rounded-full border border-border py-2.5 text-center text-sm">Verify the number</div>
          <div className="py-1 text-center text-xs text-muted-foreground underline underline-offset-4">I&apos;m sure, send anyway</div>
        </div>
      </div>
    </div>
  );
}

const FAN = [
  { q10: 1.0, q50: 14.0, q90: 39.3 },
  { q10: 1.9, q50: 14.2, q90: 38.4 },
  { q10: 2.4, q50: 12.1, q90: 30.0 },
  { q10: 2.0, q50: 11.0, q90: 27.5 },
  { q10: 2.8, q50: 13.4, q90: 33.0 },
  { q10: 3.6, q50: 15.2, q90: 35.1 },
  { q10: 2.2, q50: 10.4, q90: 26.0 },
];

function FanVisual() {
  const W = 420;
  const H = 260;
  const x = (i: number) => 30 + (i * (W - 60)) / 6;
  const y = (v: number) => H - 30 - (v / 42) * (H - 60);
  const band = `M${FAN.map((d, i) => `${x(i)},${y(d.q90)}`).join(" L")} L${[...FAN].reverse().map((d, i) => `${x(6 - i)},${y(d.q10)}`).join(" L")} Z`;
  const mid = `M${FAN.map((d, i) => `${x(i)},${y(d.q50)}`).join(" L")}`;
  return (
    <div className="mx-auto w-full max-w-[460px] rounded-3xl border border-border bg-card p-5">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium">Cash-out demand · next 7 days</p>
        <p className="label-mono">Tk thousand</p>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full" role="img" aria-label="Illustration of a 7-day cash-out forecast band and the usual cash on hand">
        <motion.path d={band} className="fill-foreground/10" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }} />
        <motion.path
          d={mid}
          fill="none"
          className="stroke-foreground"
          strokeWidth={2}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
        <line x1={20} x2={W - 20} y1={y(14.8)} y2={y(14.8)} className="stroke-risk" strokeDasharray="4 4" />
        <text x={W - 22} y={y(14.8) - 6} textAnchor="end" className="fill-risk text-[10px]">
          cash on hand
        </text>
        {["Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon"].map((d, i) => (
          <text key={d} x={x(i)} y={H - 8} textAnchor="middle" className="fill-muted-foreground text-[11px]">
            {d}
          </text>
        ))}
      </svg>
      <div className="mt-3 flex items-center justify-between rounded-2xl bg-muted/60 px-4 py-3 text-sm">
        <span>Hold for a 90%-safe Tuesday</span>
        <span className="num font-mono font-semibold">Tk 39,500</span>
      </div>
    </div>
  );
}

function CaseVisual() {
  const alerts = Array.from({ length: 14 }, (_, i) => ({ x: 40 + (i % 2) * 34, y: 24 + i * 16 }));
  const mid = [
    { x: 210, y: 70 },
    { x: 230, y: 140 },
    { x: 205, y: 210 },
  ];
  return (
    <div className="mx-auto w-full max-w-[460px] rounded-3xl border border-border bg-card p-5">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium">Linked by money paths</p>
        <p className="label-mono">≤ 3 hops · ≤ 48 h</p>
      </div>
      <svg viewBox="0 0 420 260" className="mt-3 w-full" role="img" aria-label="Illustration: many alerts joined through mule wallets into one case">
        {alerts.map((a, i) => (
          <motion.line
            key={`l${i}`}
            x1={a.x}
            y1={a.y}
            x2={mid[i % 3].x}
            y2={mid[i % 3].y}
            className="stroke-foreground/25"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.6, delay: 0.1 + i * 0.03 }}
          />
        ))}
        {mid.map((m, i) => (
          <motion.line
            key={`m${i}`}
            x1={m.x}
            y1={m.y}
            x2={350}
            y2={140}
            className="stroke-volt"
            strokeWidth={2}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.6, delay: 0.7 + i * 0.1 }}
          />
        ))}
        {alerts.map((a, i) => (
          <circle key={`a${i}`} cx={a.x} cy={a.y} r={4} className="fill-muted-foreground" />
        ))}
        {mid.map((m, i) => (
          <circle key={`w${i}`} cx={m.x} cy={m.y} r={7} className="fill-background stroke-foreground" strokeWidth={1.5} />
        ))}
        <motion.circle
          cx={350}
          cy={140}
          r={22}
          className="fill-volt"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          style={{ transformOrigin: "350px 140px" }}
          transition={{ delay: 1.1, type: "spring", stiffness: 200, damping: 14 }}
        />
        <text x={350} y={144} textAnchor="middle" className="fill-black text-[11px] font-semibold">
          1 case
        </text>
        <text x={56} y={252} textAnchor="middle" className="fill-muted-foreground text-[10px]">
          alerts
        </text>
        <text x={215} y={252} textAnchor="middle" className="fill-muted-foreground text-[10px]">
          mule wallets
        </text>
      </svg>
      <div className="mt-3 flex items-center justify-between rounded-2xl bg-muted/60 px-4 py-3 text-sm">
        <span>Accept or reject the complaint</span>
        <span className="num font-mono font-semibold">42 h left</span>
      </div>
    </div>
  );
}

const VISUALS = [PhoneVisual, FanVisual, CaseVisual];

export function Story() {
  const ref = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", (v) => setActive(Math.min(2, Math.max(0, Math.floor(v * 3)))));
  const Visual = VISUALS[active];

  return (
    <section className="border-b border-border" aria-labelledby="story-title">
      <div className="mx-auto max-w-[1760px] px-4 pt-24 md:px-8 xl:px-12 md:pt-32">
        <p className="label-mono">One evening, three people</p>
        <h2 id="story-title" className="mt-4 max-w-3xl font-serif text-5xl leading-[1] md:text-6xl">
          The same scam, seen from <span className="italic">every side</span> of the money.
        </h2>
      </div>

      {/* Desktop: pinned visual, text changes as you scroll */}
      <div ref={ref} className="relative hidden h-[300vh] md:block">
        <div className="sticky top-0 flex h-screen items-center">
          <div className="mx-auto grid w-full max-w-[1760px] grid-cols-2 items-center gap-16 px-6">
            <div className="relative">
              <div className="absolute -left-6 top-0 h-full w-px bg-border">
                <motion.div className="w-px bg-foreground" style={{ height: "100%", scaleY: scrollYProgress, transformOrigin: "top" }} />
              </div>
              <AnimatePresence mode="wait">
                <motion.div
                  key={active}
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -24 }}
                  transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}
                >
                  <ActText i={active} />
                </motion.div>
              </AnimatePresence>
              <div className="mt-10 flex gap-2" aria-hidden="true">
                {ACTS.map((_, i) => (
                  <span key={i} className={cn("h-1 rounded-full transition-all", i === active ? "w-10 bg-foreground" : "w-4 bg-border")} />
                ))}
              </div>
            </div>
            <AnimatePresence mode="wait">
              <motion.div
                key={active}
                initial={{ opacity: 0, scale: 0.96, filter: "blur(6px)" }}
                animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                exit={{ opacity: 0, scale: 0.98, filter: "blur(6px)" }}
                transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
              >
                <Visual />
                <p className="label-mono mt-4 text-center">Illustration · live numbers inside each area</p>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Mobile: simple stacked acts */}
      <div className="space-y-20 px-4 py-16 md:hidden">
        {ACTS.map((_, i) => {
          const V = VISUALS[i];
          return (
            <div key={i} className="space-y-8">
              <ActText i={i} />
              <V />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ActText({ i }: { i: number }) {
  const a = ACTS[i];
  return (
    <div>
      <p className="label-mono">
        Act {i + 1} · {a.who} · {a.time}
      </p>
      <h3 className="mt-4 text-3xl font-semibold tracking-[-0.02em] md:text-4xl">{a.title}</h3>
      <p className="mt-4 max-w-lg text-lg leading-relaxed text-muted-foreground">{a.body}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {a.ais.map((x) => (
          <span key={x} className="rounded-full border border-border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
            {x}
          </span>
        ))}
      </div>
      <Link href={a.href} className="mt-8 inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline">
        {a.cta} <ArrowUpRight className="size-4" />
      </Link>
    </div>
  );
}
