"use client";

import Link from "next/link";
import { ArrowDownLeft, ArrowUpRight, MessageSquareWarning, Send, ShieldCheck, TrendingUp } from "lucide-react";
import { AreaIntro, CustomerShell } from "@/components/customer/phone";
import { Guard } from "@/components/shell/states";
import { Inspector, InspectorSection, KV, TraceFooter } from "@/components/trust/inspector";
import { shortDate, tk } from "@/lib/format";
import { useLang } from "@/lib/i18n";
import type { Profile } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const TYPE: Record<string, string> = { p2p: "Transfer", qr_pay: "QR payment", cash_in: "Cash in", cash_out: "Cash out", recharge: "Mobile recharge", bill: "Bill" };

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
          label="Customer · Rina · synthetic persona"
          title={
            <>
              Rina&apos;s wallet, with a <span className="italic">pause</span> built in.
            </>
          }
          text="Rina is a garment worker who has used her wallet for a few months. Every transfer is checked before it leaves; she always makes the final choice."
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
      inspector={
        <Inspector>
          <InspectorSection title="What happens when Rina presses send">
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
          </InspectorSection>
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
          <InspectorSection title="Try these">
            <div className="grid gap-2 sm:grid-cols-3">
              {[
                ["/customer/send?scenario=golden_prize_scam", "Prize scam", "High risk · paused"],
                ["/customer/send?scenario=new_device_takeover", "New phone + PIN reset", "AI says not sure"],
                ["/customer/send?scenario=normal_user", "Family transfer", "Low risk · sends"],
              ].map(([href, a, b]) => (
                <Link key={href} href={href} className="rounded-2xl border border-border p-3 text-sm hover:border-foreground/40">
                  <p className="font-medium">{a}</p>
                  <p className="text-xs text-muted-foreground">{b}</p>
                </Link>
              ))}
            </div>
          </InspectorSection>
          <TraceFooter trace={q.data?.trace_id} model={q.data?.model_version || "profile"} data={q.data?.data_version} />
        </Inspector>
      }
    />
  );
}
