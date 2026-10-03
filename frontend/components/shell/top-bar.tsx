"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";
import { Logo } from "@/components/brand/logo";
import { SyntheticBadge } from "@/components/trust/chips";
import { useRecordedMode } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const AREAS = [
  { href: "/", label: "Home", who: "" },
  { href: "/customer", label: "Customer", who: "Rubab" },
  { href: "/agent", label: "Agent", who: "Tanvir" },
  { href: "/ops", label: "Operations", who: "Abdur Rahman" },
  { href: "/trust", label: "Trust Center", who: "" },
  { href: "/about", label: "About", who: "" },
];

const isActive = (path: string | null, href: string) => (href === "/" ? path === "/" : !!path?.startsWith(href));

export function TopBar({ floating = false }: { floating?: boolean }) {
  const path = usePathname();
  const mobileNav = useRef<HTMLElement>(null);
  // on phones the menu scrolls sideways: bring the current area into view
  useEffect(() => {
    const nav = mobileNav.current;
    const on = nav?.querySelector<HTMLElement>('[aria-current="page"]');
    if (nav && on) nav.scrollTo({ left: on.offsetLeft - nav.clientWidth / 2 + on.clientWidth / 2 });
  }, [path]);
  const { resolvedTheme, setTheme } = useTheme();
  const { lang, setLang } = useLang();
  const recorded = useRecordedMode();
  return (
    <header
      className={cn(
        "z-40 border-b",
        floating ? "fixed inset-x-0 top-0 border-transparent bg-background/30 backdrop-blur-md" : "sticky top-0 border-border bg-background/80 backdrop-blur-md",
      )}
    >
      <div className="mx-auto flex h-14 max-w-[1760px] items-center gap-4 px-4 md:px-8 xl:px-12">
        <Link href="/" aria-label="UVERA home">
          <Logo />
        </Link>
        <nav className="ml-2 hidden items-center gap-0.5 lg:flex" aria-label="Areas">
          {AREAS.map((a) => {
            const active = isActive(path, a.href);
            return (
              <Link
                key={a.href}
                href={a.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "whitespace-nowrap rounded-full px-3 py-1.5 text-[13px] transition-colors",
                  active ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {a.label}
                {a.who && <span className={cn("ml-1.5 hidden text-xs xl:inline", active ? "text-background/60" : "text-faint")}>{a.who}</span>}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {recorded ? (
            <span
              className="hidden items-center gap-1.5 rounded-full border border-dashed border-caution/60 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-caution sm:inline-flex"
              title="The live API is offline, so the site plays back real responses recorded from it for the demo scenarios."
            >
              ● Recorded demo
            </span>
          ) : (
            <SyntheticBadge className="hidden lg:inline-flex" />
          )}
          <button
            onClick={() => setLang(lang === "en" ? "bn" : "en")}
            className="h-8 rounded-full border border-border px-3 text-xs text-muted-foreground hover:text-foreground"
          >
            {lang === "en" ? <span lang="bn">বাংলা</span> : "English"}
            <span className="sr-only"> (change language)</span>
          </button>
          <button
            aria-label="Toggle light and dark theme"
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            className="grid size-8 place-items-center rounded-full border border-border text-muted-foreground hover:text-foreground"
          >
            <Sun className="hidden size-4 dark:block" />
            <Moon className="size-4 dark:hidden" />
          </button>
        </div>
      </div>
      <nav
        ref={mobileNav}
        className="no-scrollbar flex gap-1 overflow-x-auto border-t border-border px-4 py-2 [mask-image:linear-gradient(to_right,black_88%,transparent)] lg:hidden"
        aria-label="Areas (mobile)"
      >
        {AREAS.map((a) => (
          <Link
            key={a.href}
            href={a.href}
            aria-current={isActive(path, a.href) ? "page" : undefined}
            className={cn("shrink-0 rounded-full px-3 py-1.5 text-sm", isActive(path, a.href) ? "bg-foreground text-background" : "text-muted-foreground")}
          >
            {a.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
