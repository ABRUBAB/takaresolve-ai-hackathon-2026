"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowRight,
  BarChart3,
  Banknote,
  ChevronLeft,
  FolderKanban,
  MessageSquareWarning,
  Network,
  QrCode,
  Send,
  Store,
  TrendingUp,
  Users,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

type Service = { href: string; icon: LucideIcon; title: string; what: string; ai: string; match?: (path: string, hash: string) => boolean };
type Area = { key: string; home: string; person: string; role: string; blurb: string; services: Service[] };

export const AREAS: Record<"customer" | "agent" | "ops", Area> = {
  customer: {
    key: "customer",
    home: "/customer",
    person: "Rubab",
    role: "Customer",
    blurb: "A wallet user who sends money, gets suspicious messages and wants to save.",
    services: [
      { href: "/customer/send", icon: Send, title: "Send money safely", what: "Every transfer is checked; risky ones pause with reasons.", ai: "Pause Check · AI-1 + AI-7" },
      { href: "/customer/check", icon: MessageSquareWarning, title: "Check a suspicious SMS", what: "Paste a message: scam or not, and which words gave it away.", ai: "Scam Text Check · AI-2" },
      { href: "/customer/guardian", icon: TrendingUp, title: "See the week ahead", what: "Will the balance run low? A savings plan that stays safe.", ai: "Cash-Flow Guardian · AI-3" },
    ],
  },
  agent: {
    key: "agent",
    home: "/agent",
    person: "Tanvir",
    role: "Agent",
    blurb: "Runs a cash-in / cash-out point. Needs enough cash every day, without holding too much.",
    services: [
      { href: "/agent#cash", icon: Banknote, title: "Cash to hold each day", what: "How much cash keeps each day 90% safe, and how much more than usual.", ai: "Liquidity Copilot · AI-4" },
      { href: "/agent#forecast", icon: BarChart3, title: "Demand forecast", what: "Cash-out demand for the next 7 days with an honest range.", ai: "Liquidity Copilot · AI-4" },
      { href: "/agent#peers", icon: Users, title: "Compare with similar agents", what: "Is my activity normal for an agent of my size and area?", ai: "Peer comparison" },
      { href: "/agent#qr", icon: Store, title: "QR cash-out in my area", what: "How many shops nearby misuse QR for cash — zone level only.", ai: "QR Shield · AI-5" },
    ],
  },
  ops: {
    key: "ops",
    home: "/ops",
    person: "Abdur Rahman",
    role: "Operations analyst",
    blurb: "Reviews scam reports and suspicious shops, and must answer complaints before legal deadlines.",
    services: [
      { href: "/ops", icon: FolderKanban, title: "Case queue", what: "Many alerts joined into cases, ordered by risk and deadline.", ai: "Case Linker · AI-6", match: (p) => p === "/ops" },
      { href: "/ops/cases/CASE-0001", icon: Network, title: "Case workspace", what: "Money-path graph, evidence, brief, deadline clock, decision.", ai: "AI-6 + AI-7 + rules", match: (p) => p.startsWith("/ops/cases") },
      { href: "/ops/qr", icon: QrCode, title: "QR Shield watchlist", what: "Shops whose QR payments look like hidden cash-out.", ai: "QR Shield · AI-5", match: (p) => p.startsWith("/ops/qr") },
    ],
  },
};

/** Top of every area: who you are, the services this person gets, and where you are (with a way back). */
export function AreaServices({ area }: { area: keyof typeof AREAS }) {
  const a = AREAS[area];
  const path = usePathname() ?? "";
  const activeIdx = a.services.findIndex((s) => (s.match ? s.match(path, "") : path === s.href.split("#")[0] && !s.href.includes("#")));
  const active = activeIdx >= 0 ? a.services[activeIdx] : null;
  const atHome = path === a.home;

  return (
    <div className="border-b border-border bg-card/30">
      <div className="mx-auto max-w-[1760px] px-4 pb-6 pt-5 md:px-8 xl:px-12">
        <nav aria-label="Breadcrumb" className="mb-4 flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
          <Link href="/" className="hover:text-foreground">
            Home
          </Link>
          <span aria-hidden="true">/</span>
          {active && !atHome ? (
            <>
              <Link href={a.home} className="hover:text-foreground">
                {a.role} · {a.person}
              </Link>
              <span aria-hidden="true">/</span>
              <span className="text-foreground" aria-current="page">
                {active.title}
              </span>
            </>
          ) : (
            <span className="text-foreground" aria-current="page">
              {a.role} · {a.person}
            </span>
          )}
          {active && !atHome && (
            <Link
              href={a.home}
              className="ml-auto inline-flex h-9 items-center gap-1 rounded-full border border-border px-3 text-xs text-foreground hover:border-foreground/40"
            >
              <ChevronLeft className="size-3.5" /> Back to {a.person}&apos;s overview
            </Link>
          )}
        </nav>

        <div className="grid gap-5 lg:grid-cols-[minmax(240px,320px)_1fr] lg:items-stretch">
          <div className="flex items-center gap-4 rounded-3xl border border-border bg-background/60 p-4">
            <span className="grid size-14 shrink-0 place-items-center rounded-full bg-foreground font-serif text-2xl text-background">{a.person.charAt(0)}</span>
            <div className="min-w-0">
              <p className="label-mono">Viewing as · {a.role}</p>
              <p className="text-lg font-semibold leading-tight">{a.person}</p>
              <p className="mt-0.5 text-xs leading-snug text-muted-foreground">{a.blurb}</p>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground">
              {a.person}&apos;s services — {a.services.length} things UVERA does here. Pick one:
            </p>
            <div className={cn("grid gap-2.5 sm:grid-cols-2", a.services.length === 4 ? "xl:grid-cols-4" : "xl:grid-cols-3")}>
              {a.services.map((s, i) => {
                const on = i === activeIdx;
                return (
                  <motion.div key={s.href} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                    <Link
                      href={s.href}
                      aria-current={on ? "page" : undefined}
                      className={cn(
                        "group relative flex h-full items-start gap-3 rounded-2xl border p-3.5 transition-all",
                        on
                          ? "border-foreground bg-foreground text-background"
                          : "border-border bg-background/60 hover:-translate-y-0.5 hover:border-foreground/50 hover:shadow-lg hover:shadow-black/20",
                      )}
                    >
                      <span className={cn("grid size-10 shrink-0 place-items-center rounded-xl", on ? "bg-volt text-black" : "bg-muted group-hover:bg-volt group-hover:text-black")}>
                        <s.icon className="size-5" aria-hidden="true" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-1 text-sm font-semibold">
                          {s.title}
                          {!on && <ArrowRight className="size-3.5 opacity-50 transition-transform group-hover:translate-x-0.5 group-hover:opacity-100" />}
                        </span>
                        <span className={cn("mt-0.5 block text-xs leading-snug", on ? "text-background/70" : "text-muted-foreground")}>{s.what}</span>
                        <span className={cn("mt-1.5 block font-mono text-[10px] uppercase tracking-wider", on ? "text-background/60" : "text-faint")}>{s.ai}</span>
                      </span>
                      {on && <span className="absolute right-3 top-3 rounded-full bg-volt px-2 py-0.5 font-mono text-[9px] font-semibold uppercase text-black">You are here</span>}
                    </Link>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
