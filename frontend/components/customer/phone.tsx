"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { House, MessageSquareWarning, Send, TrendingUp } from "lucide-react";
import type { ReactNode } from "react";
import { type Key, useLang } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const TABS: { href: string; key: Key; icon: typeof House }[] = [
  { href: "/customer", key: "home", icon: House },
  { href: "/customer/send", key: "send_money", icon: Send },
  { href: "/customer/check", key: "check_sms", icon: MessageSquareWarning },
  { href: "/customer/guardian", key: "guardian", icon: TrendingUp },
];

/** The customer's app, drawn as a phone on large screens and full-width on phones. */
export function Phone({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { t, lang } = useLang();
  return (
    <div className="lg:sticky lg:top-20">
      <div className="mx-auto w-full max-w-[400px] lg:rounded-[2.75rem] lg:border lg:border-border lg:bg-background lg:p-3 lg:shadow-2xl lg:shadow-black/40">
        <div className="relative flex min-h-[720px] flex-col overflow-hidden rounded-[2.2rem] border border-border bg-card">
          <div className="flex items-center justify-between px-6 pb-2 pt-4 font-mono text-[11px] text-muted-foreground" aria-hidden="true">
            <span>19:30</span>
            <span className="h-5 w-20 rounded-full bg-background" />
            <span>4G ▮▮▮</span>
          </div>
          <div className={cn("flex-1 overflow-y-auto px-5 pb-6", lang === "bn" && "bn")}>{children}</div>
          <nav className="grid grid-cols-4 border-t border-border bg-card/95 backdrop-blur" aria-label="Customer app">
            {TABS.map((tab) => {
              const on = tab.href === "/customer" ? path === "/customer" : path?.startsWith(tab.href);
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  aria-current={on ? "page" : undefined}
                  className={cn("flex flex-col items-center gap-1 py-3 text-[11px]", on ? "text-foreground" : "text-faint hover:text-muted-foreground")}
                >
                  <tab.icon className="size-5" aria-hidden="true" />
                  <span className={cn(lang === "bn" && "bn")}>{t(tab.key)}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
      <p className="label-mono mt-3 text-center">Synthetic persona · demo wallet</p>
    </div>
  );
}

export function CustomerShell({ phone, inspector, intro, aside }: { phone: ReactNode; inspector: ReactNode; intro: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1760px] px-4 py-8 md:px-8 xl:px-12 md:py-12">
      <div className="grid items-start gap-8 lg:grid-cols-[400px_minmax(0,1fr)] lg:gap-14">
        <div className="lg:order-2 lg:pt-6">
          {intro}
          {aside && <div className="mt-8 hidden lg:block">{aside}</div>}
          <div className="mt-8 hidden lg:block">{inspector}</div>
        </div>
        <div className="lg:order-1">
          <Phone>{phone}</Phone>
        </div>
        <div className="space-y-6 lg:hidden">
          {aside}
          {inspector}
        </div>
      </div>
    </div>
  );
}

export function AreaIntro({ label, title, text }: { label: string; title: ReactNode; text?: ReactNode }) {
  return (
    <div>
      <p className="label-mono">{label}</p>
      <h1 className="mt-3 font-serif text-4xl leading-[1.05] md:text-5xl">{title}</h1>
      {text && <p className="mt-3 max-w-2xl text-muted-foreground">{text}</p>}
    </div>
  );
}
