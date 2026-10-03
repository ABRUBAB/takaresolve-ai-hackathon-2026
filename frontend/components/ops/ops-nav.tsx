"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/ops", label: "Case queue", note: "AI-6 + AI-7" },
  { href: "/ops/qr", label: "QR Shield watchlist", note: "AI-5" },
];

export function OpsNav() {
  const path = usePathname();
  return (
    <div className="border-b border-border">
      <nav className="no-scrollbar mx-auto flex max-w-[1760px] gap-6 overflow-x-auto px-4 md:px-8 xl:px-12" aria-label="Operations">
        {TABS.map((t) => {
          const on = t.href === "/ops" ? path === "/ops" || path?.startsWith("/ops/cases") : path?.startsWith(t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={on ? "page" : undefined}
              className={cn("-mb-px shrink-0 border-b-2 py-3 text-sm", on ? "border-foreground text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}
            >
              {t.label} <span className="ml-1 font-mono text-[10px] text-faint">{t.note}</span>
            </Link>
          );
        })}
        <span className="ml-auto hidden shrink-0 items-center text-xs text-faint sm:flex">Signed in as Abdur Rahman · operations analyst (demo)</span>
      </nav>
    </div>
  );
}
