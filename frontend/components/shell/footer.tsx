"use client";

import Link from "next/link";
import { ArrowUp } from "lucide-react";
import { Mark } from "@/components/brand/logo";
import { SyntheticBadge } from "@/components/trust/chips";
import { FlickeringGrid } from "@/components/ui/flickering-grid";
import { useMotionPref } from "@/lib/motion-pref";

const REPO = "https://github.com/ABRUBAB/takaresolve-ai-hackathon-2026";

const COLUMNS = [
  {
    title: "Explore",
    links: [
      { href: "/", label: "Home" },
      { href: "/customer", label: "Customer · Rina" },
      { href: "/agent", label: "Agent · Karim" },
      { href: "/ops", label: "Operations · Nusrat" },
      { href: "/trust", label: "Trust Center" },
      { href: "/about", label: "About us" },
    ],
  },
  {
    title: "Evidence",
    links: [
      { href: `${REPO}/tree/main/notebooks`, label: "Kaggle notebooks" },
      { href: `${REPO}/tree/main/docs/model_cards`, label: "Model cards" },
      { href: `${REPO}/blob/main/docs/data_card.md`, label: "Data card" },
      { href: `${REPO}/blob/main/docs/system_card.md`, label: "System card" },
      { href: `${REPO}/blob/main/docs/threat_model.md`, label: "Threat model" },
    ],
  },
  {
    title: "Project",
    links: [
      { href: REPO, label: "Source code" },
      { href: `${REPO}/blob/main/docs/architecture.md`, label: "Architecture" },
      { href: `${REPO}/blob/main/docs/third_party.md`, label: "Third-party licenses" },
      { href: `${REPO}/blob/main/LICENSE`, label: "MIT license" },
    ],
  },
];

export function Footer() {
  const { animate } = useMotionPref();
  return (
    <footer className="relative overflow-hidden border-t border-border">
      <div className="mx-auto grid max-w-7xl gap-12 px-4 pb-10 pt-16 md:grid-cols-[1.4fr_repeat(3,1fr)] md:px-6">
        <div className="space-y-5">
          <Link href="/" className="inline-flex items-center gap-2 text-lg font-semibold tracking-[-0.03em]" aria-label="UVERA home">
            <Mark className="size-7" /> UVERA
          </Link>
          <p className="max-w-xs font-serif text-2xl leading-snug">
            Trust you can <span className="italic text-volt-ink dark:text-volt">verify.</span>
          </p>
          <p className="max-w-sm text-sm text-muted-foreground">
            A trust layer for mobile money, built for AI DEV FEST 2026 (DIU-CPC), Track 07. All people, wallets, shops and messages are
            synthetic.
          </p>
          <SyntheticBadge />
        </div>
        {COLUMNS.map((c) => (
          <nav key={c.title} aria-label={c.title} className="space-y-3 text-sm">
            <p className="label-mono">{c.title}</p>
            <ul className="space-y-2">
              {c.links.map((l) => (
                <li key={l.href}>
                  {l.href.startsWith("http") ? (
                    <a href={l.href} target="_blank" rel="noreferrer" className="text-muted-foreground transition-colors hover:text-foreground">
                      {l.label}
                    </a>
                  ) : (
                    <Link href={l.href} className="text-muted-foreground transition-colors hover:text-foreground">
                      {l.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>

      <div className="relative">
        {animate && (
          <FlickeringGrid
            className="absolute inset-0 -z-0 [mask-image:linear-gradient(to_top,black,transparent)]"
            squareSize={3}
            gridGap={6}
            color="#d7ff3a"
            maxOpacity={0.18}
            flickerChance={0.08}
          />
        )}
        <p
          aria-hidden="true"
          className="relative select-none whitespace-nowrap px-4 font-serif text-[clamp(6rem,24vw,22rem)] leading-[0.78] tracking-[-0.04em] text-foreground/[0.07] md:px-6"
        >
          UVERA
        </p>
      </div>

      <div className="relative border-t border-border bg-background">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-5 text-xs text-muted-foreground md:px-6">
          <span>© 2026 UVERA team · MIT license</span>
          <span>Not affiliated with, or endorsed by, any payment provider. Not financial advice.</span>
          <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-foreground">
            <svg viewBox="0 0 24 24" className="size-3.5" fill="currentColor" aria-hidden="true">
              <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.7 5.39-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" />
            </svg>
            GitHub
          </a>
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            className="ml-auto inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 hover:text-foreground"
          >
            <ArrowUp className="size-3" /> Back to top
          </button>
        </div>
      </div>
    </footer>
  );
}
