"use client";

import Link from "next/link";
import { ArrowUpRight, BadgeCheck, CircleHelp, Eye, Hand, Languages, ScrollText } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { OutputChip } from "@/components/trust/chips";
import { CardBody, CardContainer, CardItem } from "@/components/ui/3d-card";
import { cn } from "@/lib/utils";

const PRINCIPLES = [
  { icon: Hand, title: "Never blocks", text: "The customer always decides. A hold only happens if a person approves it." },
  { icon: CircleHelp, title: "Says “not sure”", text: "Mixed evidence or an unusual case goes to a person instead of a guess." },
  { icon: Eye, title: "Shows evidence", text: "Every answer lists its reasons, the model version and a trace id." },
  { icon: Languages, title: "Bangla first", text: "Short explanations in Bangla and English, for a busy moment." },
  { icon: ScrollText, title: "Rules stay rules", text: "Limits and dispute deadlines live in config files, labelled as business rules." },
  { icon: BadgeCheck, title: "Labels everything", text: "Model estimate, business rule or generated wording: you always know which." },
];

export function Principles() {
  const [open, setOpen] = useState(0);
  return (
    <section className="border-b border-border" aria-labelledby="principles-title">
      <div className="mx-auto max-w-[1760px] px-4 py-24 md:px-8 xl:px-12 md:py-32">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label-mono">Responsible by design</p>
            <h2 id="principles-title" className="mt-4 max-w-2xl font-serif text-5xl leading-[1] md:text-6xl">
              Built to be <span className="italic">trusted</span>.
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <OutputChip type="model" />
            <OutputChip type="rule" />
            <OutputChip type="generated" />
          </div>
        </div>
        <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {PRINCIPLES.map((p, i) => {
            const on = open === i;
            return (
              <motion.div
                key={p.title}
                onMouseEnter={() => setOpen(i)}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05, duration: 0.5 }}
                className={cn("flex gap-4 rounded-3xl border p-6 transition-colors", on ? "border-foreground/50 bg-card" : "border-border bg-card/40")}
              >
                <span className={cn("grid size-11 shrink-0 place-items-center rounded-2xl transition-colors", on ? "bg-volt text-black" : "bg-muted")}>
                  <p.icon className="size-5" aria-hidden="true" />
                </span>
                <div>
                  <p className="font-semibold">{p.title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{p.text}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function MiniDial() {
  return (
    <svg viewBox="0 0 100 100" className="size-28" aria-hidden="true">
      <circle cx="50" cy="50" r="40" fill="none" className="stroke-muted" strokeWidth="8" strokeDasharray="188 252" transform="rotate(135 50 50)" strokeLinecap="round" />
      <circle cx="50" cy="50" r="40" fill="none" className="stroke-risk" strokeWidth="8" strokeDasharray="170 252" transform="rotate(135 50 50)" strokeLinecap="round" />
      <rect x="41" y="38" width="6" height="24" rx="1.5" className="fill-foreground" />
      <rect x="53" y="38" width="6" height="24" rx="1.5" className="fill-volt-ink dark:fill-volt" />
    </svg>
  );
}

function MiniBars() {
  const h = [62, 58, 46, 42, 50, 54, 40];
  return (
    <div className="flex h-28 items-end gap-1.5" aria-hidden="true">
      {h.map((v, i) => (
        <span key={i} className={cn("w-4 rounded-t-md", i < 2 ? "bg-volt-ink dark:bg-volt" : "bg-muted-foreground/40")} style={{ height: `${v + 30}%` }} />
      ))}
    </div>
  );
}

function MiniGraph() {
  const pts = [
    [12, 20], [10, 50], [14, 80], [40, 30], [44, 70], [80, 50],
  ];
  return (
    <svg viewBox="0 0 100 100" className="size-28" aria-hidden="true">
      {[[0, 3], [1, 3], [1, 4], [2, 4], [3, 5], [4, 5]].map(([a, b], i) => (
        <line key={i} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]} className="stroke-foreground/40" strokeWidth="1.5" />
      ))}
      {pts.slice(0, 5).map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i > 2 ? 5 : 3.5} className={i > 2 ? "fill-volt-ink dark:fill-volt" : "fill-muted-foreground"} />
      ))}
      <circle cx="80" cy="50" r="11" className="fill-foreground" />
    </svg>
  );
}

function MiniGauge() {
  return (
    <div className="grid h-28 w-36 grid-cols-5 items-end gap-1.5" aria-hidden="true">
      {[0.86, 0.94, 0.88, 0.48, 0].map((v, i) => (
        <span key={i} className={cn("rounded-t-md", i === 0 ? "bg-volt-ink dark:bg-volt" : "bg-muted-foreground/40")} style={{ height: `${Math.max(6, v * 100)}%` }} />
      ))}
    </div>
  );
}

const PORTALS = [
  { href: "/customer", who: "Rubab", role: "Customer", text: "Send with a Pause Check, check an SMS, see the week ahead.", Visual: MiniDial },
  { href: "/agent", who: "Tanvir", role: "Agent", text: "Cash to hold each day and the riskiest days.", Visual: MiniBars },
  { href: "/ops", who: "Abdur Rahman", role: "Operations", text: "One case with evidence, a brief and a deadline clock.", Visual: MiniGraph },
  { href: "/trust", who: "Judges", role: "Trust Center", text: "Every metric, fairness slice and limitation.", Visual: MiniGauge },
];

export function Portals() {
  return (
    <section aria-labelledby="portals-title">
      <div className="mx-auto max-w-[1760px] px-4 py-24 md:px-8 xl:px-12 md:py-32">
        <p className="label-mono">One website · four doors</p>
        <h2 id="portals-title" className="mt-4 font-serif text-5xl leading-[1] md:text-6xl">
          Walk in as <span className="italic">anyone</span>.
        </h2>
        <div className="mt-6 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-4">
          {PORTALS.map((p) => (
            <CardContainer key={p.href} containerClassName="py-6" className="w-full">
              <CardBody className="h-auto w-full">
                <Link
                  href={p.href}
                  className="group relative flex h-[340px] w-full flex-col justify-between overflow-hidden rounded-3xl border border-border bg-card p-6 transition-colors hover:border-foreground/40"
                >
                  <CardItem translateZ={30} className="flex w-full items-start justify-between">
                    <span className="label-mono">{p.role}</span>
                    <ArrowUpRight className="size-5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                  </CardItem>
                  <CardItem translateZ={70} className="mx-auto">
                    <p.Visual />
                  </CardItem>
                  <CardItem translateZ={40}>
                    <h3 className="font-serif text-4xl">{p.who}</h3>
                    <p className="mt-1 min-h-10 text-sm text-muted-foreground">{p.text}</p>
                  </CardItem>
                  <span className="absolute inset-x-0 bottom-0 h-0.5 origin-left scale-x-0 bg-volt transition-transform duration-500 group-hover:scale-x-100" />
                </Link>
              </CardBody>
            </CardContainer>
          ))}
        </div>
      </div>
    </section>
  );
}
