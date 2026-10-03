"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowRight, MousePointerClick, Pause, Play } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Mark } from "@/components/brand/logo";
import type { WorldCompact } from "@/components/home/trust-scene";
import Magnet from "@/components/reactbits/Magnet";
import { HyperText } from "@/components/ui/hyper-text";
import { Marquee } from "@/components/ui/marquee";
import { useIdle } from "@/lib/use-idle";
import { useMotionPref } from "@/lib/motion-pref";
import { cn } from "@/lib/utils";

const TrustScene = dynamic(() => import("@/components/home/trust-scene"), { ssr: false });

const subscribeWidth = (cb: () => void) => {
  window.addEventListener("resize", cb);
  return () => window.removeEventListener("resize", cb);
};
const useMobile = () => useSyncExternalStore(subscribeWidth, () => window.innerWidth < 768, () => false);

const MODES = [
  { label: "Everyday money", caption: "Every dot is a wallet in the synthetic world. Grey sparks are everyday payments." },
  { label: "Three layers", caption: "Customers, agents & shops, operations: the three areas of UVERA. Scam money (volt) stops halfway." },
  { label: "The pause", caption: "The whole network becomes one promise: pause a risky transfer before the money moves." },
  { label: "One case", caption: "Alerts that share money paths collapse into one case for the operations team." },
];
const STEP_MS = 6500;

const TICKER = [
  { who: "Tk 3,000 → C008170", what: "Paused", p: "90%", tone: "text-risk" },
  { who: "Tk 500 → C003608", what: "Sent", p: "<1%", tone: "text-safe" },
  { who: "Tk 9,000 · new phone", what: "Not sure → a person checks", p: "", tone: "text-unsure" },
  { who: "“You won Tk 50,000”", what: "Prize scam SMS", p: "98%", tone: "text-risk" },
  { who: "CASE-0001", what: "132 alerts → 1 case", p: "42 h left", tone: "text-volt-ink dark:text-volt" },
  { who: "Shop M00120", what: "QR cash-out pattern", p: "review", tone: "text-caution" },
  { who: "Agent A0161", what: "Hold Tk 39,500 on Tuesday", p: "90%-safe", tone: "text-foreground" },
];

export function Hero() {
  const { resolvedTheme } = useTheme();
  const { animate, paused, setPaused } = useMotionPref();
  const mobile = useMobile();
  const idle = useIdle();
  const [world, setWorld] = useState<WorldCompact | null>(null);
  const [visible, setVisible] = useState(true);
  const [mode, setMode] = useState(0);
  const [auto, setAuto] = useState(true);
  const box = useRef<HTMLElement>(null);

  useEffect(() => {
    let alive = true;
    fetch("/data/world-sample.json")
      .then((r) => r.json())
      .then((d: WorldCompact) => alive && setWorld(d))
      .catch(() => alive && setWorld(null));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { threshold: 0.02 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const playing = auto && animate && visible;
  useEffect(() => {
    if (!playing) return;
    const id = setTimeout(() => setMode((m) => (m + 1) % MODES.length), STEP_MS);
    return () => clearTimeout(id);
  }, [playing, mode]);

  const tabs = (compact: boolean) => (
    <div role="tablist" aria-label="What the 3D field shows" className={cn("inline-flex flex-wrap gap-1 rounded-full border border-border bg-background/70 p-1 backdrop-blur-md", compact && "w-full justify-between")}>
      {MODES.map((m, i) => (
        <button
          key={m.label}
          role="tab"
          aria-selected={mode === i}
          onClick={() => {
            setMode(i);
            setAuto(false);
          }}
          className={cn(
            "relative overflow-hidden rounded-full transition-colors",
            compact ? "h-9 px-2.5 text-[11px]" : "h-9 px-3.5 text-[12.5px]",
            mode === i ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {m.label}
          {mode === i && playing && (
            <motion.span
              key={`p${mode}`}
              className="absolute inset-x-3 bottom-1 h-px origin-left bg-background/60"
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: STEP_MS / 1000, ease: "linear" }}
            />
          )}
        </button>
      ))}
    </div>
  );

  return (
    <section ref={box} className="relative isolate h-[100svh] min-h-[600px] overflow-hidden border-b border-border" aria-labelledby="hero-title">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_72%_45%,color-mix(in_oklab,var(--volt)_7%,transparent),transparent_60%)]" />
      <motion.div
        className="absolute inset-x-0 bottom-12 top-14 -z-10 opacity-60 md:left-[36%] md:opacity-100"
        initial={{ opacity: 0, scale: 1.04 }}
        animate={{ opacity: world && idle ? 1 : 0, scale: world && idle ? 1 : 1.04 }}
        transition={{ duration: 1.8, ease: [0.2, 0.8, 0.2, 1] }}
        role="img"
        aria-label={`Interactive 3D field of synthetic wallets. Current view: ${MODES[mode].label}. ${MODES[mode].caption}`}
      >
        {world && idle && <TrustScene world={world} mode={mode} dark={resolvedTheme !== "light"} animate={animate && visible} mobile={mobile} />}
      </motion.div>
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-r from-background via-background/50 to-transparent md:via-background/10 md:to-40%" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-40 bg-gradient-to-t from-background to-transparent" />
      <div className="grain" />

      {/* view switcher: top-right corner, over the field */}
      <motion.div
        className="absolute right-4 top-28 z-10 hidden max-w-md flex-col items-end gap-2 md:right-6 md:flex lg:top-[4.5rem]"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1, duration: 0.6 }}
      >
        {tabs(false)}
        <AnimatePresence mode="wait">
          <motion.p
            key={mode}
            className="max-w-sm text-right text-xs leading-relaxed text-muted-foreground"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25 }}
          >
            {MODES[mode].caption}
          </motion.p>
        </AnimatePresence>
        <p className="flex items-center gap-1.5 font-mono text-[10.5px] text-faint">
          <MousePointerClick className="size-3.5" /> move through the field · click for a shockwave
        </p>
      </motion.div>

      <div className="pointer-events-none mx-auto flex h-full max-w-[1760px] flex-col justify-center px-4 pb-16 pt-16 md:px-8 xl:px-12">
        <motion.div
          className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
        >
          <span className="inline-flex items-center gap-2.5 text-[clamp(1.6rem,2.6vw,2.4rem)] font-semibold leading-none tracking-[-0.04em]">
            <Mark className="size-[1.1em]" animated />
            UVERA
          </span>
          <span className="label-mono border-l border-border pl-4">AI DEV FEST 2026 · Track 07</span>
        </motion.div>
        <h1 id="hero-title" className="max-w-4xl font-serif text-[clamp(3rem,min(8.6vw,13.5vh),8.75rem)] leading-[0.9] tracking-[-0.02em]">
          <motion.span
            className="block"
            initial={{ opacity: 0, y: 30, filter: "blur(10px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.9, delay: 0.1, ease: [0.2, 0.8, 0.2, 1] }}
          >
            Trust you can
          </motion.span>
          <span className="block italic text-volt-ink dark:text-volt">
            <HyperText as="span" preserveCase className="pointer-events-auto inline-block py-0 font-serif text-[1em] font-normal italic" duration={1400} delay={600} characterSet={"abcdefghijklmnopqrstuvwxyz".split("")}>
              verify.
            </HyperText>
          </span>
        </h1>
        <motion.p
          className="mt-[clamp(1rem,3vh,2rem)] max-w-md text-base leading-relaxed text-muted-foreground md:text-lg"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          A trust layer for mobile money. It pauses a scam <span className="text-foreground">before the money moves</span>, and every answer shows its evidence.
        </motion.p>
        <motion.div
          className="pointer-events-auto mt-[clamp(1.25rem,4vh,2.5rem)] flex flex-wrap items-center gap-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
        >
          <Magnet padding={60} magnetStrength={6} disabled={!animate || mobile}>
            <a
              href="#live"
              className="group inline-flex h-12 items-center gap-2 rounded-full bg-volt px-7 text-sm font-semibold text-black shadow-[0_0_40px_-8px_var(--volt)]"
            >
              Run a scam through it
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </a>
          </Magnet>
          <Link
            href="/trust"
            className="inline-flex h-12 items-center rounded-full border border-border bg-background/50 px-7 text-sm font-medium backdrop-blur hover:border-foreground/40"
          >
            See the evidence
          </Link>
        </motion.div>
        <div className="pointer-events-auto mt-6 md:hidden">{tabs(true)}</div>
      </div>

      <div className="absolute inset-x-0 bottom-0 border-t border-border/60 bg-background/60 backdrop-blur-md">
        <div className="flex items-center">
          <span className="label-mono hidden shrink-0 border-r border-border px-4 md:block">Live demo decisions</span>
          <Marquee pauseOnHover className={cn("flex-1 [--duration:48s] [--gap:2.5rem]", paused && "[&_*]:[animation-play-state:paused]")} repeat={3}>
            {TICKER.map((t) => (
              <span key={t.who} className="flex items-center gap-2 whitespace-nowrap font-mono text-xs">
                <span className="text-muted-foreground">{t.who}</span>
                <span className={cn("font-medium", t.tone)}>{t.what}</span>
                {t.p && <span className="text-faint">{t.p}</span>}
              </span>
            ))}
          </Marquee>
          <button
            onClick={() => setPaused(!paused)}
            className="mx-3 inline-flex shrink-0 items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
            aria-pressed={paused}
          >
            {paused ? <Play className="size-3" /> : <Pause className="size-3" />}
            <span className="hidden sm:inline">{paused ? "Play motion" : "Pause motion"}</span>
          </button>
        </div>
      </div>
    </section>
  );
}
