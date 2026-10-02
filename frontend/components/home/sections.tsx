import Link from "next/link";
import { ArrowUpRight, BadgeCheck, CircleHelp, Eye, Hand, Languages, ScrollText } from "lucide-react";
import { OutputChip } from "@/components/trust/chips";

const AIS = [
  {
    id: "AI-1",
    name: "Pause Check",
    who: "Customer",
    what: "Scores a transfer before it is sent and pauses it with reasons when it looks like a scam.",
    how: "LightGBM vs XGBoost, CatBoost, logistic regression and a rule · grouped CV × 5 seeds · isotonic calibration · conformal “not sure” · TreeSHAP reasons",
    out: "model" as const,
  },
  {
    id: "AI-2",
    name: "Scam Text Check",
    who: "Customer",
    what: "Reads a pasted SMS in Bangla, Banglish or English and names the scam family, highlighting the phrases that matter.",
    how: "TF-IDF vs BGE-M3 embeddings vs an evidential head · tested on a held-out writing style · phrase occlusion",
    out: "model" as const,
  },
  {
    id: "AI-3",
    name: "Cash-Flow Guardian",
    who: "Customer",
    what: "Forecasts the next 7 days of money in and out and warns early if the balance may fall below a safety floor.",
    how: "Seasonal-naive vs LightGBM-quantile vs Chronos-2 · rolling-origin backtest · empirical probability",
    out: "model" as const,
  },
  {
    id: "AI-4",
    name: "Liquidity Copilot",
    who: "Agent",
    what: "Tells an agent how much cash to hold for a 90%-safe day and highlights the riskiest days of the week.",
    how: "Quantile forecasts · interval coverage · no yes/no alarm where the evidence is weak",
    out: "model" as const,
  },
  {
    id: "AI-5",
    name: "QR Shield",
    who: "Operations · Agent (zone only)",
    what: "Finds shops whose QR payments look like hidden cash-out, compared with shops of the same type, area and size.",
    how: "LightGBM + Isolation Forest rank fusion · unseen scheme tested separately · size-fairness check",
    out: "model" as const,
  },
  {
    id: "AI-6",
    name: "Case Linker",
    who: "Operations",
    what: "Follows money paths in time order and joins alerts that share wallets or shops into one case with a dispute clock.",
    how: "Time-respecting path tracing (≤ 3 hops, ≤ 48 h) · union-find linking · community detection",
    out: "rule" as const,
  },
  {
    id: "AI-7",
    name: "Grounded Brief",
    who: "Everyone",
    what: "Writes a short Bangla and English explanation using only the facts the other AIs produced.",
    how: "Gemini structured output · evidence-card retrieval · deterministic validator · template fallback · injection tests",
    out: "generated" as const,
  },
];

export function AiGrid() {
  return (
    <section className="border-b border-border" aria-labelledby="ais-title">
      <div className="mx-auto max-w-7xl px-4 py-24 md:px-6 md:py-32">
        <p className="label-mono">Seven AIs · one trust layer</p>
        <h2 id="ais-title" className="mt-4 max-w-3xl font-serif text-5xl leading-[1] md:text-6xl">
          Each one compared with a <span className="italic">simpler baseline</span>.
        </h2>
        <div className="mt-14 grid gap-px overflow-hidden rounded-3xl border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
          {AIS.map((a) => (
            <article key={a.id} className="group flex flex-col gap-4 bg-background p-6 transition-colors hover:bg-card">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-faint">{a.id}</span>
                <OutputChip type={a.out} />
              </div>
              <div>
                <h3 className="text-xl font-semibold tracking-[-0.02em]">{a.name}</h3>
                <p className="mt-0.5 text-xs text-faint">{a.who}</p>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">{a.what}</p>
              <p className="mt-auto border-t border-border pt-4 font-mono text-[11px] leading-relaxed text-faint">{a.how}</p>
            </article>
          ))}
          <article className="flex flex-col justify-between gap-4 bg-foreground p-6 text-background">
            <span className="font-mono text-xs opacity-60">NB00 + NB99</span>
            <div>
              <h3 className="text-xl font-semibold tracking-[-0.02em]">A synthetic world, then one evaluation</h3>
              <p className="mt-2 text-sm opacity-70">
                2.2 million seeded events with hidden scam processes and honest look-alikes, a leakage guard, and one notebook that
                gathers every result.
              </p>
            </div>
            <Link href="/trust" className="inline-flex items-center gap-1 text-sm font-medium">
              Data card and results <ArrowUpRight className="size-4" />
            </Link>
          </article>
        </div>
      </div>
    </section>
  );
}

const PRINCIPLES = [
  { icon: Hand, title: "Never blocks", text: "The customer always decides. A hold only happens if a person approves it." },
  { icon: CircleHelp, title: "Says “not sure”", text: "When the evidence is mixed or the case is unusual, it asks a person instead of guessing." },
  { icon: Eye, title: "Shows its evidence", text: "Every answer lists its reasons, the model version and a trace id you can look up." },
  { icon: Languages, title: "Bangla first", text: "Explanations in Bangla and English, short enough for a busy moment." },
  { icon: ScrollText, title: "Rules stay rules", text: "Limits and dispute deadlines live in config files, labelled as business rules, never hidden in a model." },
  { icon: BadgeCheck, title: "Labels every output", text: "Model estimate, business rule or generated wording: you always know which one you are reading." },
];

export function Principles() {
  return (
    <section className="border-b border-border" aria-labelledby="principles-title">
      <div className="mx-auto grid max-w-7xl gap-12 px-4 py-24 md:grid-cols-[1fr_2fr] md:px-6 md:py-32">
        <div>
          <p className="label-mono">Responsible by design</p>
          <h2 id="principles-title" className="mt-4 font-serif text-5xl leading-[1] md:text-6xl">
            Built to be <span className="italic">trusted</span>, not just accurate.
          </h2>
          <div className="mt-8 flex flex-wrap gap-2">
            <OutputChip type="model" />
            <OutputChip type="rule" />
            <OutputChip type="generated" />
            <OutputChip type="assumption" />
          </div>
        </div>
        <div className="grid gap-x-10 gap-y-10 sm:grid-cols-2">
          {PRINCIPLES.map((p) => (
            <div key={p.title} className="flex gap-4">
              <p.icon className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <div>
                <h3 className="font-semibold">{p.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{p.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const PORTALS = [
  { href: "/customer", who: "Rina", role: "Customer", text: "Send money with a Pause Check, check a suspicious SMS, and see the week ahead.", n: "01" },
  { href: "/agent", who: "Karim", role: "Agent", text: "Cash to hold for each day, the riskiest days, and QR cash-out pressure in the area.", n: "02" },
  { href: "/ops", who: "Nusrat", role: "Operations", text: "Linked cases with evidence, dispute deadlines, a grounded brief and human decisions.", n: "03" },
  { href: "/trust", who: "Judges & reviewers", role: "Trust Center", text: "Every metric, fairness slice, model card, limitation and live system health.", n: "04" },
];

export function Portals() {
  return (
    <section aria-labelledby="portals-title">
      <div className="mx-auto max-w-7xl px-4 py-24 md:px-6 md:py-32">
        <p className="label-mono">One website · four doors</p>
        <h2 id="portals-title" className="mt-4 font-serif text-5xl leading-[1] md:text-6xl">
          Walk in as anyone.
        </h2>
        <div className="mt-14 grid gap-4 md:grid-cols-2">
          {PORTALS.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="group relative flex min-h-56 flex-col justify-between overflow-hidden rounded-3xl border border-border bg-card p-6 transition-colors hover:border-foreground/40"
            >
              <div className="flex items-start justify-between">
                <span className="font-mono text-xs text-faint">{p.n}</span>
                <ArrowUpRight className="size-5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </div>
              <div>
                <p className="label-mono">{p.role}</p>
                <h3 className="mt-2 font-serif text-4xl">{p.who}</h3>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">{p.text}</p>
              </div>
              <span className="absolute inset-x-0 bottom-0 h-0.5 origin-left scale-x-0 bg-volt transition-transform duration-500 group-hover:scale-x-100" />
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
