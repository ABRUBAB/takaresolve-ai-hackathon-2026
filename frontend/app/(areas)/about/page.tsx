"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowUpRight, CircleHelp, Eye, Hand } from "lucide-react";
import { motion } from "motion/react";
import { BlurFade } from "@/components/ui/blur-fade";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Timeline } from "@/components/ui/timeline";
import { useMotionPref } from "@/lib/motion-pref";
import { useIdle } from "@/lib/use-idle";
import { TEAM, TEAM_NAME } from "@/lib/team";

const LiquidMetal = dynamic(() => import("@paper-design/shaders-react").then((m) => m.LiquidMetal), { ssr: false });

const WHY = [
  { n: "01", icon: Hand, title: "Why", text: "A scam transfer finishes in seconds. The people it hurts are often new to digital money, and nobody asks them to pause." },
  { n: "02", icon: Eye, title: "How", text: "Seven AIs on a seeded synthetic world of 2.2 million events. Each one is compared with a simpler baseline and tested on people it never saw." },
  { n: "03", icon: CircleHelp, title: "Principles", text: "Never block. Say “not sure” when unsure. Show the evidence. A person approves every hold, and every number comes from a notebook run." },
];

const STEPS = [
  {
    title: "Day 1",
    content: (
      <div className="space-y-2 text-sm text-muted-foreground">
        <p className="text-base text-foreground">A world to learn from</p>
        <p>We built a seeded synthetic world: 20,000 customers, 600 agents, 2,500 shops and 120 days of activity, with hidden scam processes, honest look-alikes, label noise and a leakage guard.</p>
      </div>
    ),
  },
  {
    title: "Day 2",
    content: (
      <div className="space-y-2 text-sm text-muted-foreground">
        <p className="text-base text-foreground">Seven AIs, nine notebooks</p>
        <p>Every model ran on Kaggle against a baseline: grouped cross-validation, calibration, conformal “not sure”, exact TreeSHAP reasons, rolling forecasts and a grounded Gemini brief with a validator.</p>
      </div>
    ),
  },
  {
    title: "Day 3",
    content: (
      <div className="space-y-2 text-sm text-muted-foreground">
        <p className="text-base text-foreground">One website for everyone</p>
        <p>Customer, agent and operations areas on a live API, a Trust Center that reads the notebook results, and this 3D field drawn from the same synthetic world.</p>
      </div>
    ),
  },
  {
    title: "7 Oct",
    content: (
      <div className="space-y-2 text-sm text-muted-foreground">
        <p className="text-base text-foreground">The on-site final</p>
        <p>A live demo, the report and the evidence, side by side.</p>
      </div>
    ),
  },
];

export default function AboutPage() {
  const { animate } = useMotionPref();
  const idle = useIdle(2500);
  return (
    <div>
      <section className="relative overflow-hidden border-b border-border">
        <div className="mx-auto grid max-w-[1760px] items-center gap-10 px-4 py-20 md:px-8 xl:px-12 lg:grid-cols-[1.3fr_1fr] lg:py-28">
          <div>
            <BlurFade delay={0.05}>
              <p className="label-mono">About us</p>
            </BlurFade>
            <BlurFade delay={0.15}>
              <h1 className="mt-5 font-serif text-[clamp(3rem,7vw,6.5rem)] leading-[0.95] tracking-[-0.02em]">
                We build AI that <span className="italic text-volt-ink dark:text-volt">pauses</span>, explains, and lets people decide.
              </h1>
            </BlurFade>
            <BlurFade delay={0.3}>
              <p className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground">
                UVERA (from Latin <em>vera</em>, “true”) is a trust layer for mobile money in Bangladesh, built by the {TEAM_NAME} for AI DEV FEST 2026, Track 07.
              </p>
            </BlurFade>
          </div>
          <div className="relative mx-auto aspect-square w-full max-w-[420px]" role="img" aria-label="The UVERA mark in liquid metal">
            <div className="absolute inset-[8%] rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--volt)_18%,transparent),transparent_65%)]" />
            {idle && <LiquidMetal
              image="/brand/mark.svg"
              colorBack="#00000000"
              colorTint="#d7ff3a"
              repetition={3}
              softness={0.25}
              shiftRed={0.25}
              shiftBlue={0.25}
              distortion={0.08}
              contour={0.4}
              angle={70}
              scale={0.85}
              speed={animate ? 0.8 : 0}
              style={{ width: "100%", height: "100%" }}
            />}
          </div>
        </div>
      </section>

      <section className="border-b border-border">
        <div className="mx-auto grid max-w-[1760px] gap-4 px-4 py-20 md:grid-cols-3 md:px-8 xl:px-12">
          {WHY.map((w, i) => (
            <motion.div
              key={w.n}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.6 }}
              className="rounded-3xl border border-border bg-card p-7"
            >
              <div className="flex items-center justify-between">
                <span className="font-serif text-5xl text-volt-ink dark:text-volt">{w.n}</span>
                <w.icon className="size-6 text-muted-foreground" />
              </div>
              <h2 className="mt-6 text-xl font-semibold">{w.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{w.text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="border-b border-border">
        <div className="mx-auto grid max-w-[1760px] grid-cols-2 gap-8 px-4 py-16 md:grid-cols-5 md:px-8 xl:px-12">
          {[
            [72, "hours to build", ""],
            [9, "Kaggle notebooks", ""],
            [7, "AI components", ""],
            [2.2, "synthetic events", "M"],
            [0, "real customer records used", ""],
          ].map(([v, label, unit]) => (
            <div key={String(label)}>
              <p className="num font-serif text-6xl leading-none md:text-7xl">
                <NumberTicker value={Number(v)} decimalPlaces={Number(v) % 1 ? 1 : 0} />
                {unit}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">{label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-b border-border">
        <div className="mx-auto max-w-[1760px] px-4 pt-20 md:px-8 xl:px-12">
          <p className="label-mono">How it came together</p>
          <h2 className="mt-4 font-serif text-5xl leading-[1] md:text-6xl">
            Seventy-two hours, <span className="italic">in order</span>.
          </h2>
        </div>
        <Timeline data={STEPS} />
      </section>

      <section className="border-b border-border">
        <div className="mx-auto max-w-[1760px] px-4 py-20 md:px-8 xl:px-12">
          <p className="label-mono">The team</p>
          <h2 className="mt-4 font-serif text-5xl leading-[1] md:text-6xl">
            Three people, <span className="italic">one weekend</span>.
          </h2>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {TEAM.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.6 }}
                className="group rounded-3xl border border-border bg-card p-7 transition-colors hover:border-foreground/40"
              >
                <div className="grid size-16 place-items-center rounded-full bg-foreground font-serif text-3xl text-background transition-colors group-hover:bg-volt group-hover:text-black">
                  {(m.initial ?? m.name.charAt(0)) || "·"}
                </div>
                <p className="mt-6 text-xl font-semibold">{m.name || "Team member"}</p>
                <p className="text-sm text-volt-ink dark:text-volt">{m.role}</p>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{m.work}</p>
                {m.github && (
                  <a href={`https://github.com/${m.github}`} target="_blank" rel="noreferrer" className="mt-5 inline-flex items-center gap-1 text-sm underline-offset-4 hover:underline">
                    github.com/{m.github} <ArrowUpRight className="size-3.5" />
                  </a>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto grid max-w-[1760px] gap-10 px-4 py-20 md:grid-cols-2 md:px-8 xl:px-12">
          <div>
            <p className="label-mono">Honest by default</p>
            <h2 className="mt-4 font-serif text-4xl leading-tight">What this is, and what it is not.</h2>
          </div>
          <ul className="space-y-4 text-sm leading-relaxed text-muted-foreground">
            <li>All people, wallets, shops and messages are synthetic. Results show that the method works, not real-world accuracy.</li>
            <li>This is an independent hackathon prototype. It is not affiliated with, or endorsed by, any payment provider, and it describes no provider&apos;s internal problems.</li>
            <li>Every external dataset, model, API and component is listed with its license in the repository.</li>
            <li>
              Want the evidence?{" "}
              <Link href="/trust" className="text-foreground underline underline-offset-4">
                Open the Trust Center
              </Link>
              .
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
}
