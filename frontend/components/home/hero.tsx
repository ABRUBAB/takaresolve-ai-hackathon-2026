"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowRight, MousePointerClick, Pause, Play } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { WorldCompact } from "@/components/home/trust-scene";
import Magnet from "@/components/reactbits/Magnet";
import { HyperText } from "@/components/ui/hyper-text";
import { Marquee } from "@/components/ui/marquee";
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

  return (
    <section ref={box} className="relative isolate min-h-[100svh] overflow-hidden border-b border-border" aria-labelledby="hero-title">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_70%_40%,color-mix(in_oklab,var(--volt)_7%,transparent),transparent_60%)]" />
      <motion.div
        className="absolute inset-0 -z-10 md:left-[18%]"
        initial={{ opacity: 0, scale: 1.04 }}
        animate={{ opacity: world ? 1 : 0, scale: world ? 1 : 1.04 }}
        transition={{ duration: 1.8, ease: [0.2, 0.8, 0.2, 1] }}
        role="img"
        aria-label={`Interactive 3D field of synthetic wallets. Current view: ${MODES[mode].label}. ${MODES[mode].caption}`}
      >
        {world && <TrustScene world={world} mode={mode} dark={resolvedTheme !== "light"} animate={animate && visible} mobile={mobile} />}
      </motion.div>
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-r from-background via-background/60 to-transparent md:via-background/20" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-56 bg-gradient-to-t from-background to-transparent" />
      <div className="grain" />

      <div className="pointer-events-none mx-auto flex min-h-[100svh] max-w-7xl flex-col justify-center px-4 pb-36 pt-28 md:px-6">
        <motion.p className="label-mono mb-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }}>
          AI DEV FEST 2026 · Track 07 · synthetic demo
        </motion.p>
        <h1 id="hero-title" className="max-w-4xl font-serif text-[clamp(3.4rem,9.5vw,9rem)] leading-[0.9] tracking-[-0.02em]">
          <motion.span
            className="block"
            initial={{ opacity: 0, y: 30, filter: "blur(10px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}
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
          className="mt-8 max-w-md text-lg leading-relaxed text-muted-foreground md:text-xl"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          Pause a scam <span className="text-foreground">before the money moves</span>. Every answer shows its evidence.
        </motion.p>
        <motion.div
          className="pointer-events-auto mt-10 flex flex-wrap items-center gap-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
        >
          <Magnet padding={60} magnetStrength={6} disabled={!animate || mobile}>
            <a
              href="#live"
              className="group inline-flex h-13 items-center gap-2 rounded-full bg-volt px-7 text-sm font-semibold text-black shadow-[0_0_40px_-8px_var(--volt)]"
            >
              Run a scam through it
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </a>
          </Magnet>
          <Link
            href="/trust"
            className="inline-flex h-13 items-center rounded-full border border-border bg-background/50 px-7 text-sm font-medium backdrop-blur hover:border-foreground/40"
          >
            See the evidence
          </Link>
        </motion.div>

        <motion.div
          className="pointer-events-auto mt-14 max-w-xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.1, duration: 0.8 }}
        >
          <div role="tablist" aria-label="What the 3D field shows" className="inline-flex flex-wrap gap-1 rounded-full border border-border bg-background/70 p-1 backdrop-blur-md">
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
                  "relative h-10 overflow-hidden rounded-full px-4 text-[13px] transition-colors",
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
          <AnimatePresence mode="wait">
            <motion.p
              key={mode}
              className="mt-3 pl-2 text-sm text-muted-foreground"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.3 }}
            >
              {MODES[mode].caption}
            </motion.p>
          </AnimatePresence>
          <p className="mt-2 hidden items-center gap-1.5 pl-2 font-mono text-[11px] text-faint md:flex">
            <MousePointerClick className="size-3.5" /> Move the mouse through the field · click it to send a shockwave
          </p>
        </motion.div>
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
