"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowRight, Pause, Play } from "lucide-react";
import { motion } from "motion/react";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { WorldCompact } from "@/components/home/trust-field";
import { useMotionPref } from "@/lib/motion-pref";

const TrustField = dynamic(() => import("@/components/home/trust-field"), { ssr: false });

const subscribeWidth = (cb: () => void) => {
  window.addEventListener("resize", cb);
  return () => window.removeEventListener("resize", cb);
};
const useMobile = () => useSyncExternalStore(subscribeWidth, () => window.innerWidth < 768, () => false);

const LEGEND = [
  { label: "Customers", cls: "bg-neutral-400" },
  { label: "Agents & shops", cls: "bg-foreground" },
  { label: "Linked cases (operations)", cls: "bg-volt-ink dark:bg-volt size-2.5" },
  { label: "Scam money, paused", cls: "ring-2 ring-volt-ink dark:ring-volt bg-transparent" },
];

function Words({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  return (
    <span className={className}>
      {text.split(" ").map((w, i) => (
        <motion.span
          key={i}
          className="inline-block whitespace-pre"
          initial={{ opacity: 0, y: "0.35em", filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.7, delay: delay + i * 0.07, ease: [0.2, 0.8, 0.2, 1] }}
        >
          {w + (i < text.split(" ").length - 1 ? " " : "")}
        </motion.span>
      ))}
    </span>
  );
}

export function Hero() {
  const { resolvedTheme } = useTheme();
  const { animate, paused, setPaused } = useMotionPref();
  const mobile = useMobile();
  const [world, setWorld] = useState<WorldCompact | null>(null);
  const [visible, setVisible] = useState(true);
  const box = useRef<HTMLDivElement>(null);

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

  return (
    <section ref={box} className="relative isolate min-h-[100svh] overflow-hidden border-b border-border" aria-labelledby="hero-title">
      <div className="absolute inset-0 -z-10 grid-bg opacity-40 [mask-image:radial-gradient(ellipse_at_60%_40%,black,transparent_70%)]" />
      <motion.div
        className="absolute inset-0 -z-10 md:left-[22%]"
        initial={{ opacity: 0 }}
        animate={{ opacity: world ? 1 : 0 }}
        transition={{ duration: 1.6, ease: "easeOut" }}
        role="img"
        aria-label="A live 3D sample of the synthetic world: customers at the bottom, agents and shops in the middle, linked cases at the top. Scam transfers stop at a pause ring, then rise into one case."
      >
        {world && (
          <TrustField world={world} dark={resolvedTheme !== "light"} animate={animate && visible} mobile={mobile} />
        )}
      </motion.div>
      <div className="absolute inset-0 -z-10 bg-gradient-to-r from-background via-background/70 to-transparent md:via-background/40" />
      <div className="absolute inset-x-0 bottom-0 -z-10 h-40 bg-gradient-to-t from-background to-transparent" />
      <div className="grain" />

      <div className="mx-auto flex min-h-[100svh] max-w-7xl flex-col justify-center px-4 pb-28 pt-28 md:px-6">
        <motion.p
          className="label-mono mb-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          AI DEV FEST 2026 · Track 07 · Open innovation for digital finance
        </motion.p>
        <h1 id="hero-title" className="max-w-4xl font-serif text-[clamp(3.2rem,9vw,8.5rem)] leading-[0.92] tracking-[-0.02em]">
          <Words text="Trust you can" />
          <br />
          <Words text="verify." className="italic text-volt-ink dark:text-volt" delay={0.3} />
        </h1>
        <motion.p
          className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground md:text-xl"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.7 }}
        >
          UVERA is a trust layer for mobile money. It <span className="text-foreground">pauses a scam before the money moves</span>,
          helps agents keep enough cash, spots QR codes used as hidden cash-out, and joins scattered alerts into one case.
          Every answer shows its evidence.
        </motion.p>
        <motion.div
          className="mt-10 flex flex-wrap items-center gap-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.9 }}
        >
          <a
            href="#live"
            className="group inline-flex h-12 items-center gap-2 rounded-full bg-volt px-6 text-sm font-semibold text-black transition-transform hover:-translate-y-0.5"
          >
            Try the Pause Check live
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </a>
          <Link
            href="/trust"
            className="inline-flex h-12 items-center rounded-full border border-border bg-background/60 px-6 text-sm font-medium backdrop-blur hover:border-foreground/40"
          >
            See how it was measured
          </Link>
        </motion.div>
      </div>

      <div className="absolute inset-x-0 bottom-0 border-t border-border/60 bg-background/50 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 md:px-6">
          <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5" aria-label="Legend for the 3D field">
            {LEGEND.map((l) => (
              <li key={l.label} className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className={`inline-block size-2 rounded-full ${l.cls}`} aria-hidden="true" />
                {l.label}
              </li>
            ))}
          </ul>
          <p className="label-mono hidden lg:block">2.2M synthetic events · 20,000 customers · 600 agents · 2,500 shops</p>
          <button
            onClick={() => setPaused(!paused)}
            className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
            aria-pressed={paused}
          >
            {paused ? <Play className="size-3" /> : <Pause className="size-3" />}
            {paused ? "Play motion" : "Pause motion"}
          </button>
        </div>
      </div>
    </section>
  );
}
