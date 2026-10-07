"use client";

import { CalendarClock, CircleHelp, KeyRound, LogOut, Phone as PhoneIcon, Timer, Users, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";
import { RiskDial } from "@/components/trust/visuals";
import { TapHint } from "@/components/ui/tap-hint";
import { tk } from "@/lib/format";
import { ALERTS, CASES, SINGLE, type Bi, type L } from "@/lib/study";
import { cn } from "@/lib/utils";

/** The customer app's phone frame (same look as components/customer/phone.tsx, without the app's tab bar). */
export function PhoneFrame({ children, lang }: { children: ReactNode; lang: L }) {
  return (
    <div className="mx-auto w-full max-w-[380px] overflow-hidden rounded-[2.2rem] border border-border bg-card" aria-label="Demo phone screen">
      <div className="flex items-center justify-between px-6 pb-2 pt-4 font-mono text-[11px] text-muted-foreground" aria-hidden="true">
        <span>19:30</span>
        <span className="h-5 w-20 rounded-full bg-background" />
        <span>4G ▮▮▮</span>
      </div>
      <div className={cn("px-5 pb-6", lang === "bn" && "bn")} lang={lang}>
        {children}
      </div>
    </div>
  );
}

type Tile = { icon: LucideIcon; value: Bi; label: Bi; text: Bi };

/** Reason tiles as the Pause Check shows them (the three strongest model reasons); tap one to read the sentence. */
function Tiles({ tiles, lang }: { tiles: Tile[]; lang: L }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        {tiles.map((t, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setOpen(open === i ? null : i)}
            aria-expanded={open === i}
            className={cn(
              "flex min-h-24 flex-col items-center justify-center gap-1 rounded-2xl border px-1 py-3 text-center transition-colors",
              open === i ? "border-foreground/50 bg-muted" : "border-border bg-background/40",
            )}
          >
            <t.icon className="size-5 text-risk" aria-hidden="true" />
            <span className="num font-mono text-sm font-semibold">{t.value[lang]}</span>
            <span className="text-[10.5px] leading-tight text-muted-foreground">{t.label[lang]}</span>
          </button>
        ))}
      </div>
      {open !== null ? (
        <p className="rounded-xl bg-muted/60 px-3 py-2 text-sm">{tiles[open].text[lang]}</p>
      ) : (
        <TapHint className="text-[11px]">{lang === "bn" ? "কারণে ট্যাপ করে পড়ুন" : "Tap a reason to read it"}</TapHint>
      )}
    </div>
  );
}

const SENDERS = (n: number): Tile => ({
  icon: Users,
  value: { bn: `${n}`, en: `${n}` },
  label: { bn: "জন এই সপ্তাহে টাকা পাঠিয়েছে", en: "people paid them this week" },
  text: { bn: "সম্প্রতি অনেক আলাদা মানুষ এই প্রাপককে টাকা পাঠিয়েছে", en: "Many different people sent money to this receiver recently" },
});
const MOVES_ON = (v: string): Tile => ({
  icon: LogOut,
  value: { bn: v, en: v },
  label: { bn: "টাকা দ্রুত বের হয়ে যায়", en: "of money moves on" },
  text: { bn: "এই প্রাপকের কাছে আসা টাকা দ্রুত বের হয়ে যায়", en: "Money sent to this receiver usually leaves quickly" },
});

/** Replicates the Pause Check result for the prize-scam transfer (recorded from the live API: p = 0.904, confident). */
export function PauseMock({ lang }: { lang: L }) {
  const tiles: Tile[] = [
    SENDERS(19),
    MOVES_ON(">99%"),
    {
      icon: CalendarClock,
      value: { bn: "12 দিন", en: "12 d" },
      label: { bn: "প্রাপকের ওয়ালেটের বয়স", en: "receiver wallet age" },
      text: { bn: "প্রাপকের ওয়ালেটটি মাত্র 12 দিন পুরোনো", en: "The receiving wallet is only 12 days old" },
    },
  ];
  return (
    <PhoneFrame lang={lang}>
      <div className="space-y-5 pt-2">
        <div className="text-center">
          <RiskDial p={0.904} size={190} className="mx-auto" label={lang === "bn" ? "প্রতারণার সম্ভাবনা" : "chance this is a scam"} />
          <div className="mt-4 flex items-center justify-center gap-2">
            <span className="flex gap-1" aria-hidden="true">
              <span className="h-5 w-1.5 rounded-sm bg-foreground" />
              <span className="h-5 w-1.5 rounded-sm bg-volt" />
            </span>
            <p className="text-xl font-semibold">{lang === "bn" ? "আপনার নিরাপত্তার জন্য থামানো হয়েছে" : "Paused for your safety"}</p>
          </div>
          <p className="num mt-1 text-sm text-muted-foreground">{tk(3000)} → C008170</p>
        </div>
        <Tiles tiles={tiles} lang={lang} />
        <div className="pointer-events-none space-y-2 select-none" aria-hidden="true">
          <span className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-foreground font-medium text-background">
            <Timer className="size-4" /> {lang === "bn" ? "১০ মিনিট অপেক্ষা করুন" : "Wait 10 minutes"}
          </span>
          <span className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border font-medium">
            <PhoneIcon className="size-4" /> {lang === "bn" ? "নম্বরটি যাচাই করুন" : "Verify the number"}
          </span>
          <span className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border font-medium">
            <Users className="size-4" /> {lang === "bn" ? "বিশ্বস্ত কাউকে জিজ্ঞেস করুন" : "Ask someone I trust"}
          </span>
          <span className="block w-full py-2 text-center text-sm text-muted-foreground underline underline-offset-4">
            {lang === "bn" ? "আমি নিশ্চিত, পাঠাব" : "I'm sure, send anyway"}
          </span>
          <p className="text-center text-xs text-faint">{lang === "bn" ? "আপনাকে কখনো আটকানো হবে না। সিদ্ধান্ত আপনার।" : "You are never blocked. You decide."}</p>
        </div>
      </div>
    </PhoneFrame>
  );
}

/** Replicates the grey "Not sure" result for the new phone + PIN reset transfer (recorded: p = 0.904, input unlike training data). */
export function UnsureMock({ lang }: { lang: L }) {
  const tiles: Tile[] = [
    SENDERS(21),
    MOVES_ON("99%"),
    {
      icon: KeyRound,
      value: { bn: "পিন", en: "PIN" },
      label: { bn: "৩ দিনের মধ্যে রিসেট", en: "reset in 3 days" },
      text: { bn: "সম্প্রতি আপনার পিন রিসেট করা হয়েছে", en: "Your PIN was reset recently" },
    },
  ];
  return (
    <PhoneFrame lang={lang}>
      <div className="space-y-5 pt-2">
        <div className="text-center">
          <RiskDial p={0.904} size={190} className="mx-auto" tone="unsure" label={lang === "bn" ? "এআই নিশ্চিত নয়" : "the AI is not sure"} />
          <div className="mt-4 flex items-center justify-center gap-2">
            <CircleHelp className="size-5 shrink-0 text-unsure" aria-hidden="true" />
            <p className="text-xl font-semibold">{lang === "bn" ? "নিশ্চিত নয় — একজন কর্মী যাচাই করবেন" : "Not sure — a person will check"}</p>
          </div>
          <p className="num mt-1 text-sm text-muted-foreground">{tk(9000)} → C008007</p>
        </div>
        <Tiles tiles={tiles} lang={lang} />
        <p className="rounded-2xl border border-dashed border-unsure/60 px-3 py-2 text-center text-sm text-muted-foreground">
          {lang === "bn" ? "এই পরিস্থিতিটি এআই যা থেকে শিখেছে তার মতো নয়।" : "This situation looks unlike what the AI learned from."}
        </p>
        <div className="pointer-events-none space-y-2 select-none" aria-hidden="true">
          <span className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border font-medium">
            <PhoneIcon className="size-4" /> {lang === "bn" ? "নম্বরটি যাচাই করুন" : "Verify the number"}
          </span>
          <span className="block w-full py-2 text-center text-sm text-muted-foreground underline underline-offset-4">
            {lang === "bn" ? "আমি নিশ্চিত, পাঠাব" : "I'm sure, send anyway"}
          </span>
          <p className="text-center text-xs text-faint">{lang === "bn" ? "আপনাকে কখনো আটকানো হবে না। সিদ্ধান্ত আপনার।" : "You are never blocked. You decide."}</p>
        </div>
      </div>
    </PhoneFrame>
  );
}

const pct0 = (p: number) => `${Math.round(p * 100)}%`;

/** Version A: the plain alert queue. The shared wallet is only visible in the receiver / next-hop column. */
export function TriageList({ lang }: { lang: L }) {
  const h = lang === "bn" ? ["সতর্কতা", "প্রেরক", "প্রাপক / এরপর গেছে", "পরিমাণ", "ঝুঁকি"] : ["Alert", "Sender", "Receiver / next hop", "Amount", "Risk"];
  return (
    <div className="overflow-x-auto rounded-2xl border border-border bg-card">
      <table className="w-full min-w-[330px] text-left">
        <thead className="bg-muted/50 text-[11px] text-muted-foreground">
          <tr>
            {h.map((c, i) => (
              <th key={c} className={cn("px-2 py-2 font-normal", i >= 3 && "text-right")}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border font-mono text-[12px]">
          {ALERTS.map((a) => (
            <tr key={a.id}>
              <td className="px-2 py-2">
                <span className="block">{a.id}</span>
                <span className="block text-[10.5px] text-faint">{a.time}</span>
              </td>
              <td className="px-2 py-2">{a.sender}</td>
              <td className="px-2 py-2">
                <span className="block">{a.receiver}</span>
                <span className="block text-[10.5px] text-muted-foreground">→ {a.next === "—" ? "—" : a.next}</span>
              </td>
              <td className="num px-2 py-2 text-right">{a.amount.toLocaleString("en-US")}</td>
              <td className="num px-2 py-2 text-right">{pct0(a.risk)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="border-t border-border px-3 py-2 text-[11px] text-faint">{lang === "bn" ? "পরিমাণ টাকায় · বানানো তথ্য" : "Amounts in Tk · synthetic data"}</p>
    </div>
  );
}

/** Version B: the same 12 alerts, already linked into cases by the shared wallet (what the Case Linker shows). */
export function TriageCases({ lang }: { lang: L }) {
  const bn = lang === "bn";
  return (
    <div className="space-y-2.5">
      {CASES.map((c) => {
        const victims = new Set(c.alerts.map((a) => a.sender)).size;
        const total = c.alerts.reduce((s, a) => s + a.amount, 0);
        return (
          <div key={c.id} className="rounded-2xl border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs text-muted-foreground">{bn ? "কেস" : "Case"} {c.id}</span>
              <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                {bn ? "সময়সীমা" : "Deadline"} · {c.deadline[lang]}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{bn ? "যৌথ ওয়ালেট (যেখানে টাকা শেষে যায়)" : "Shared wallet (where the money ends up)"}</p>
            <p className="font-mono text-2xl font-semibold tracking-tight">{c.wallet}</p>
            {c.via.length > 0 && (
              <p className="mt-0.5 font-mono text-[11px] text-faint">
                {bn ? "মাধ্যম" : "via"} {c.via.join(" · ")}
              </p>
            )}
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <Stat v={`${c.alerts.length}`} l={bn ? "সতর্কতা" : "alerts"} />
              <Stat v={`${victims}`} l={bn ? "ভুক্তভোগী" : "victims"} />
              <Stat v={tk(total)} l={bn ? "মোট" : "total"} />
            </div>
            <p className="mt-2 font-mono text-[10.5px] text-faint">{c.alerts.map((a) => a.id).join(" · ")}</p>
          </div>
        );
      })}
      {SINGLE.map((a) => (
        <div key={a.id} className="rounded-2xl border border-dashed border-border p-4">
          <p className="text-xs text-muted-foreground">{bn ? "একক সতর্কতা (কোনো কেসের সাথে যুক্ত নয়)" : "Single alert (not linked to a case)"}</p>
          <p className="mt-1 font-mono text-sm">
            {a.id} · {a.sender} → {a.receiver} · {tk(a.amount)} · {pct0(a.risk)}
          </p>
        </div>
      ))}
    </div>
  );
}

function Stat({ v, l }: { v: string; l: string }) {
  return (
    <div className="rounded-xl bg-muted/50 px-1 py-2">
      <p className="num font-mono text-sm font-semibold">{v}</p>
      <p className="text-[10.5px] text-muted-foreground">{l}</p>
    </div>
  );
}
