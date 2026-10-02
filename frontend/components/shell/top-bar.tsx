"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Logo } from "@/components/brand/logo";
import { SyntheticBadge } from "@/components/trust/chips";
import { useLang } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const AREAS = [
  { href: "/customer", label: "Customer", who: "Rina" },
  { href: "/agent", label: "Agent", who: "Karim" },
  { href: "/ops", label: "Operations", who: "Nusrat" },
  { href: "/trust", label: "Trust Center", who: "" },
];

export function TopBar({ floating = false }: { floating?: boolean }) {
  const path = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const { lang, setLang } = useLang();
  return (
    <header
      className={cn(
        "z-40 border-b",
        floating ? "fixed inset-x-0 top-0 border-transparent bg-background/30 backdrop-blur-md" : "sticky top-0 border-border bg-background/80 backdrop-blur-md",
      )}
    >
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 md:px-6">
        <Link href="/" aria-label="UVERA home">
          <Logo />
        </Link>
        <nav className="ml-2 hidden items-center gap-1 md:flex" aria-label="Areas">
          {AREAS.map((a) => {
            const active = path?.startsWith(a.href);
            return (
              <Link
                key={a.href}
                href={a.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-full px-3 py-1.5 text-sm transition-colors",
                  active ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {a.label}
                {a.who && <span className={cn("ml-1.5 text-xs", active ? "text-background/60" : "text-faint")}>{a.who}</span>}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <SyntheticBadge className="hidden lg:inline-flex" />
          <button
            onClick={() => setLang(lang === "en" ? "bn" : "en")}
            className="h-8 rounded-full border border-border px-3 text-xs text-muted-foreground hover:text-foreground"
            aria-label={lang === "en" ? "Switch to Bangla" : "Switch to English"}
          >
            {lang === "en" ? "বাংলা" : "English"}
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
      <nav className="no-scrollbar flex gap-1 overflow-x-auto border-t border-border px-4 py-2 md:hidden" aria-label="Areas (mobile)">
        {AREAS.map((a) => (
          <Link
            key={a.href}
            href={a.href}
            className={cn("shrink-0 rounded-full px-3 py-1 text-sm", path?.startsWith(a.href) ? "bg-foreground text-background" : "text-muted-foreground")}
          >
            {a.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
