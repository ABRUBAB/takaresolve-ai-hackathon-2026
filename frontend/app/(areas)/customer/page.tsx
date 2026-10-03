"use client";

import Link from "next/link";
import { ArrowDownLeft, ArrowUpRight, CircleHelp, MessageSquareWarning, Send, ShieldCheck, ShieldX, TrendingUp } from "lucide-react";
import { AreaIntro, CustomerShell } from "@/components/customer/phone";
import { Guard } from "@/components/shell/states";
import { Inspector, InspectorSection, KV, SummaryChips, TraceFooter } from "@/components/trust/inspector";
import { shortDate, tk } from "@/lib/format";
import { useLang } from "@/lib/i18n";
import type { Profile } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const TYPE: Record<string, string> = { p2p: "Transfer", qr_pay: "QR payment", cash_in: "Cash in", cash_out: "Cash out", recharge: "Mobile recharge", bill: "Bill" };

const TRY = [
  { href: "/customer/send?scenario=golden_prize_scam", title: "Prize scam", sub: "High risk · paused", icon: ShieldX, bg: "bg-risk/15", fg: "text-risk" },
  { href: "/customer/send?scenario=new_device_takeover", title: "New phone at night", sub: "The AI is not sure", icon: CircleHelp, bg: "bg-muted", fg: "text-unsure" },
  { href: "/customer/send?scenario=normal_user", title: "Family transfer", sub: "Low risk · sends", icon: ShieldCheck, bg: "bg-safe/15", fg: "text-safe" },
];

const PIPELINE = [
  ["Features", "19 behaviour signals about the sender, the receiver and the moment, computed only from the past"],
  ["Score", "LightGBM, chosen over XGBoost, CatBoost and logistic regression by a pre-registered rule"],
  ["Calibrate", "Isotonic calibration turns the score into an honest probability"],
  ["Doubt", "Conformal prediction + an unusual-input detector decide when to say “not sure”"],
  ["Decide", "Business rules in a config file pick the actions; the customer is never blocked"],
  ["Explain", "TreeSHAP reasons + Bangla/English brief, checked by a validator"],
];

export default function CustomerHome() {
  const q = useApi<Profile>("/customers/C000021/profile", "customer");
  const { t } = useLang();
  return (
    <CustomerShell
      intro={
        <AreaIntro
          label="Customer · Rubab · synthetic persona"
          title={
            <>
              Rubab&apos;s wallet, with a <span className="italic">pause</span> built in.
            </>
          }
          text="Rubab is a garment worker who has used a mobile wallet for a few months. Every transfer is checked before it leaves; Rubab always makes the final choice."
        />
      }
      phone={
        <Guard q={q}>
          {(p) => (
            <div className="space-y-6 pt-2">
              <div>
                <p className="text-sm text-muted-foreground">{t("hello")},</p>
                <p className="text-2xl font-semibold tracking-tight">{p.display_name}</p>
              </div>
              <div className="relative overflow-hidden rounded-3xl bg-foreground p-5 text-background">
                <p className="text-xs opacity-60">{t("available")}</p>
                <p className="num mt-1 font-mono text-3xl font-semibold tracking-tight">{tk(p.balance_bdt)}</p>
                <p className="mt-4 flex items-center gap-1.5 text-xs opacity-70">
                  <ShieldCheck className="size-3.5 text-volt" /> Pause Check is on
                </p>
                <span className="absolute -right-6 -top-6 size-28 rounded-full border-[10px] border-volt/20" aria-hidden="true" />
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { href: "/customer/send", icon: Send, label: t("send_money") },
                  { href: "/customer/check", icon: MessageSquareWarning, label: t("check_sms") },
                  { href: "/customer/guardian", icon: TrendingUp, label: t("guardian") },
                ].map((a) => (
                  <Link key={a.href} href={a.href} className="flex flex-col items-center gap-2 rounded-2xl border border-border p-3 text-center text-xs hover:border-foreground/40">
                    <a.icon className="size-5" aria-hidden="true" />
                    {a.label}
                  </Link>
                ))}
              </div>
              <Link
                href="/customer/send?scenario=golden_prize_scam"
                className="block rounded-2xl border border-dashed border-volt-ink/60 p-4 text-sm dark:border-volt/50"
              >
                <p className="font-medium">New message: “You won Tk 50,000!”</p>
                <p className="mt-1 text-muted-foreground">Try sending the Tk 3,000 “processing fee” and see the Pause Check →</p>
              </Link>
              <div>
                <p className="mb-2 text-sm font-medium">{t("recent")}</p>
                <ul className="divide-y divide-border">
                  {p.recent.slice(0, 6).map((r, i) => (
                    <li key={i} className="flex items-center gap-3 py-2.5">
                      <span className="grid size-8 place-items-center rounded-full bg-muted">
                        {r.direction === "in" ? <ArrowDownLeft className="size-4" /> : <ArrowUpRight className="size-4" />}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm">{TYPE[r.type] ?? r.type}</p>
                        <p className="truncate text-xs text-faint">
                          {r.counterparty} · {shortDate(r.time)}
                        </p>
                      </div>
                      <span className="num font-mono text-sm">
                        {r.direction === "in" ? "+" : "−"}
                        {tk(r.amount)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Guard>
      }
      aside={
        <div className="space-y-8">
          <div className="rounded-3xl border border-border bg-card p-5">
            <p className="label-mono mb-4">What happens when Rubab presses send</p>
            <ol className="space-y-3">
              {PIPELINE.map(([k, v], i) => (
                <li key={k} className="flex gap-3">
                  <span className="num mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border border-border font-mono text-[11px]">{i + 1}</span>
                  <p className="text-sm">
                    <span className="font-medium">{k}.</span> <span className="text-muted-foreground">{v}</span>
                  </p>
                </li>
              ))}
            </ol>
          </div>
          <div>
          <p className="label-mono mb-3">Try a moment from Rubab&apos;s evening</p>
          <div className="grid gap-3 sm:grid-cols-3">
            {TRY.map((x) => (
              <Link key={x.href} href={x.href} className="group rounded-3xl border border-border bg-card p-4 transition-colors hover:border-foreground/40">
                <span className={`mb-4 grid size-10 place-items-center rounded-full ${x.bg}`}>
                  <x.icon className={`size-5 ${x.fg}`} />
                </span>
                <p className="font-medium">{x.title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{x.sub}</p>
              </Link>
            ))}
          </div>
          </div>
        </div>
      }
      inspector={
        <Inspector summary={<SummaryChips items={[["balance", q.data ? tk(q.data.balance_bdt) : "—"], ["wallet age", q.data ? `${q.data.tenure_days} d` : "—"], ["checks", "19 signals"]]} />}>
          {q.data && (
            <InspectorSection title="Persona facts (synthetic)">
              <KV
                rows={[
                  ["Wallet", q.data.customer_id],
                  ["Area", q.data.zone],
                  ["Usual channel", q.data.channel],
                  ["Language", q.data.language],
                  ["Wallet age", `${q.data.tenure_days} days`],
                  ["Demo date", q.data.today],
                ]}
              />
            </InspectorSection>
          )}
          <TraceFooter trace={q.data?.trace_id} model={q.data?.model_version || "profile"} data={q.data?.data_version} />
        </Inspector>
      }
    />
  );
}
