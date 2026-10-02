"use client";

import { BrainCircuit, FileCog, MessageSquareText, Network, ScanSearch, Smartphone, Sparkles, UserCheck, Users } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { forwardRef, useRef, useState, type RefObject } from "react";
import { AnimatedBeam } from "@/components/ui/animated-beam";
import { useMotionPref } from "@/lib/motion-pref";
import { cn } from "@/lib/utils";

type NodeInfo = { id: string; label: string; sub: string; icon: typeof Smartphone; text: string; tone?: "volt" | "plain" | "rule" | "gen" };

const NODES: Record<string, NodeInfo> = {
  transfer: { id: "transfer", label: "Transfer", sub: "amount, receiver, moment", icon: Smartphone, text: "Rina presses send. Only the transfer facts and recent wallet behaviour are used." },
  sms: { id: "sms", label: "Message", sub: "the SMS she got", icon: MessageSquareText, text: "If she pastes the message that asked for money, it is checked too." },
  ai1: { id: "ai1", label: "AI-1 Score", sub: "LightGBM + calibration", icon: BrainCircuit, text: "19 behaviour signals → a calibrated scam probability with exact TreeSHAP reasons.", tone: "volt" },
  ai2: { id: "ai2", label: "AI-2 Text", sub: "scam family + phrases", icon: ScanSearch, text: "Names the scam family and highlights the words that moved the verdict.", tone: "volt" },
  doubt: { id: "doubt", label: "Doubt check", sub: "conformal + novelty", icon: Sparkles, text: "If both answers are plausible, or the case is unlike anything seen before, the answer becomes “not sure”." },
  policy: { id: "policy", label: "Rules", sub: "config, not model", icon: FileCog, text: "Business rules in a YAML file pick the actions. The customer is never blocked.", tone: "rule" },
  brief: { id: "brief", label: "AI-7 Brief", sub: "grounded, validated", icon: Sparkles, text: "Gemini may only reword the facts above; a validator rejects anything new.", tone: "gen" },
  rina: { id: "rina", label: "Rina decides", sub: "wait · verify · send", icon: UserCheck, text: "She sees why, in Bangla, and chooses. Nothing is blocked." },
  ai6: { id: "ai6", label: "AI-6 Linker", sub: "money paths → case", icon: Network, text: "Paused transfers that share mule wallets or shops are joined into one case." },
  nusrat: { id: "nusrat", label: "Nusrat reviews", sub: "a person decides holds", icon: Users, text: "Operations sees one case with evidence and a deadline clock, and signs every decision." },
};

const Node = forwardRef<HTMLButtonElement, { n: NodeInfo; active: boolean; onPick: () => void }>(function Node({ n, active, onPick }, ref) {
  const Icon = n.icon;
  return (
    <button ref={ref} onClick={onPick} aria-pressed={active} className="group z-10 flex flex-col items-center gap-2 text-center">
      <span
        className={cn(
          "grid size-14 place-items-center rounded-2xl border bg-card transition-all md:size-16",
          active ? "scale-110 border-foreground shadow-[0_0_40px_-10px_var(--volt)]" : "border-border group-hover:border-foreground/40",
          n.tone === "volt" && "border-volt-ink/60 dark:border-volt/50",
        )}
      >
        <Icon className={cn("size-6", n.tone === "volt" ? "text-volt-ink dark:text-volt" : n.tone === "rule" ? "text-rule" : n.tone === "gen" ? "text-generated" : "")} />
      </span>
      <span className="text-xs font-medium md:text-sm">{n.label}</span>
      <span className="hidden text-[11px] text-faint md:block">{n.sub}</span>
    </button>
  );
});

export function DecisionFlow() {
  const box = useRef<HTMLDivElement>(null);
  const r_transfer = useRef<HTMLButtonElement>(null);
  const r_sms = useRef<HTMLButtonElement>(null);
  const r_ai1 = useRef<HTMLButtonElement>(null);
  const r_ai2 = useRef<HTMLButtonElement>(null);
  const r_doubt = useRef<HTMLButtonElement>(null);
  const r_policy = useRef<HTMLButtonElement>(null);
  const r_brief = useRef<HTMLButtonElement>(null);
  const r_rina = useRef<HTMLButtonElement>(null);
  const r_ai6 = useRef<HTMLButtonElement>(null);
  const r_nusrat = useRef<HTMLButtonElement>(null);
  const [active, setActive] = useState("ai1");
  const { animate } = useMotionPref();
  const beam = (from: RefObject<HTMLButtonElement | null>, to: RefObject<HTMLButtonElement | null>, delay: number, curvature = 0, volt = false) => (
    <AnimatedBeam
      containerRef={box}
      fromRef={from as RefObject<HTMLElement | null>}
      toRef={to as RefObject<HTMLElement | null>}
      curvature={curvature}
      delay={delay}
      duration={animate ? 4 : 1e9}
      pathColor="var(--foreground)"
      pathOpacity={0.12}
      gradientStartColor={volt ? "#d7ff3a" : "#a3a3a3"}
      gradientStopColor={volt ? "#d7ff3a" : "#fafafa"}
    />
  );
  const pick = (id: string) => () => setActive(id);

  return (
    <section className="border-b border-border" aria-labelledby="flow-title">
      <div className="mx-auto max-w-7xl px-4 py-24 md:px-6 md:py-32">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label-mono">How one decision is made</p>
            <h2 id="flow-title" className="mt-4 max-w-2xl font-serif text-5xl leading-[1] md:text-6xl">
              From a tap on <span className="italic">send</span> to a person&apos;s choice.
            </h2>
          </div>
          <p className="max-w-xs text-sm text-muted-foreground">Tap any step.</p>
        </div>

        <div ref={box} className="relative mt-14 overflow-hidden rounded-3xl border border-border bg-card/40 px-3 py-10 md:px-10">
          <div className="grid grid-cols-5 items-center gap-y-12">
            <div className="flex flex-col items-center gap-12">
              <Node ref={r_transfer} n={NODES.transfer} active={active === "transfer"} onPick={pick("transfer")} />
              <Node ref={r_sms} n={NODES.sms} active={active === "sms"} onPick={pick("sms")} />
            </div>
            <div className="flex flex-col items-center gap-8">
              <Node ref={r_ai1} n={NODES.ai1} active={active === "ai1"} onPick={pick("ai1")} />
              <Node ref={r_ai2} n={NODES.ai2} active={active === "ai2"} onPick={pick("ai2")} />
            </div>
            <div className="flex flex-col items-center gap-12">
              <Node ref={r_doubt} n={NODES.doubt} active={active === "doubt"} onPick={pick("doubt")} />
              <Node ref={r_policy} n={NODES.policy} active={active === "policy"} onPick={pick("policy")} />
            </div>
            <div className="flex flex-col items-center gap-12">
              <Node ref={r_brief} n={NODES.brief} active={active === "brief"} onPick={pick("brief")} />
              <Node ref={r_ai6} n={NODES.ai6} active={active === "ai6"} onPick={pick("ai6")} />
            </div>
            <div className="flex flex-col items-center gap-12">
              <Node ref={r_rina} n={NODES.rina} active={active === "rina"} onPick={pick("rina")} />
              <Node ref={r_nusrat} n={NODES.nusrat} active={active === "nusrat"} onPick={pick("nusrat")} />
            </div>
          </div>
          <span key="transfer-ai1">{beam(r_transfer, r_ai1, 0, 0, true)}</span>
          <span key="sms-ai2">{beam(r_sms, r_ai2, 0.3)}</span>
          <span key="ai1-doubt">{beam(r_ai1, r_doubt, 0.6, -10, true)}</span>
          <span key="ai1-policy">{beam(r_ai1, r_policy, 0.8, 10)}</span>
          <span key="ai2-policy">{beam(r_ai2, r_policy, 0.9)}</span>
          <span key="doubt-policy">{beam(r_doubt, r_policy, 1.1)}</span>
          <span key="policy-brief">{beam(r_policy, r_brief, 1.4, -10, true)}</span>
          <span key="policy-ai6">{beam(r_policy, r_ai6, 1.6, 10)}</span>
          <span key="brief-rina">{beam(r_brief, r_rina, 1.9, 0, true)}</span>
          <span key="ai6-nusrat">{beam(r_ai6, r_nusrat, 2.1)}</span>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={active}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="mx-auto mt-6 flex max-w-2xl items-start gap-3 rounded-2xl border border-border bg-card px-5 py-4"
          >
            <span className="mt-0.5 font-mono text-xs text-volt-ink dark:text-volt">{NODES[active].label}</span>
            <p className="text-sm text-muted-foreground">{NODES[active].text}</p>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
