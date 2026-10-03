"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUpRight, QrCode } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { AreaIntro } from "@/components/customer/phone";
import { DeadlineBar, DeadlineRing, StatusPill } from "@/components/ops/bits";
import { Guard } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { num, tk } from "@/lib/format";
import type { Cases } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

export default function OpsQueue() {
  const q = useApi<Cases>("/cases?limit=60", "ops");
  const [detailed, setDetailed] = useState(true);
  const router = useRouter();

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-12">
      <AreaIntro
        label="Operations · Nusrat · AI-6 Case Linker"
        title={
          <>
            Many alerts, <span className="italic">one case</span>.
          </>
        }
        text="Flagged transfers, mule wallets and suspicious QR shops that share money paths are joined into one case. The queue is ordered by risk and by how close the next dispute deadline is."
      />
      <Guard q={q}>
        {(d) => {
          const urgent = d.cases.filter((c) => c.next_deadline?.status === "urgent").length;
          const atRisk = d.cases.reduce((s, c) => s + c.amount_at_risk_bdt, 0);
          const alerts = d.cases.reduce((s, c) => s + c.n_alerts, 0);
          return (
            <div className="mt-10 space-y-6">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ["Linked cases", num(d.total)],
                  [`Alerts inside the top ${d.cases.length}`, num(alerts)],
                  ["Deadlines due soon", num(urgent)],
                  ["Money at risk (top cases)", tk(atRisk)],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-2xl border border-border bg-card p-4">
                    <p className="text-xs text-muted-foreground">{k}</p>
                    <p className="num mt-1 font-mono text-2xl font-semibold">{v}</p>
                  </div>
                ))}
              </div>

              <div>
                <p className="label-mono mb-3">Act first · nearest deadlines</p>
                <div className="grid gap-3 md:grid-cols-3">
                  {[...d.cases]
                    .filter((c) => c.next_deadline)
                    .sort((a, b) => (a.next_deadline?.remaining_hours ?? 1e9) - (b.next_deadline?.remaining_hours ?? 1e9))
                    .slice(0, 3)
                    .map((c, i) => (
                      <motion.div key={c.case_key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
                        <Link
                          href={`/ops/cases/${c.case_key}`}
                          className="flex items-center gap-5 rounded-3xl border border-border bg-card p-5 transition-colors hover:border-foreground/40"
                        >
                          {c.next_deadline && <DeadlineRing d={c.next_deadline} size={84} />}
                          <div className="min-w-0">
                            <p className="font-mono text-lg font-semibold">{c.case_key}</p>
                            <p className="text-sm text-muted-foreground">
                              {c.victims} victims · {tk(c.amount_at_risk_bdt)}
                            </p>
                            <p className="mt-2 inline-flex items-center gap-1 text-xs">
                              Open case <ArrowUpRight className="size-3" />
                            </p>
                          </div>
                        </Link>
                      </motion.div>
                    ))}
                </div>
              </div>

              <div className="overflow-hidden rounded-3xl border border-border bg-card">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3">
                  <p className="text-sm font-medium">Case queue</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => setDetailed((v) => !v)}
                      aria-pressed={detailed}
                      className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      {detailed ? "Simple view" : "Detailed view"}
                    </button>
                    <OutputChip type="model">Linking + score</OutputChip>
                    <OutputChip type="rule">Deadlines</OutputChip>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className={cn("w-full text-sm", detailed ? "min-w-[860px]" : "min-w-[640px]")}>
                    <thead className="text-left text-xs text-muted-foreground">
                      <tr className="border-b border-border">
                        <th className="px-5 py-2.5 font-normal">Case</th>
                        <th className="px-3 py-2.5 font-normal">Score</th>
                        {detailed && <th className="px-3 py-2.5 font-normal">Alerts</th>}
                        <th className="px-3 py-2.5 font-normal">Victims</th>
                        {detailed && <th className="px-3 py-2.5 font-normal">Wallets · shops · agents</th>}
                        <th className="px-3 py-2.5 text-right font-normal">At risk</th>
                        <th className="px-3 py-2.5 font-normal">Next deadline</th>
                        <th className="px-5 py-2.5 font-normal">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {d.cases.map((c, i) => (
                        <motion.tr
                          key={c.case_key}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: Math.min(i, 20) * 0.02 }}
                          onClick={() => router.push(`/ops/cases/${c.case_key}`)}
                          className="cursor-pointer hover:bg-muted/50"
                        >
                          <td className="px-5 py-3">
                            <Link href={`/ops/cases/${c.case_key}`} className="font-mono font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                              {c.case_key}
                            </Link>
                            {c.qr_flagged_endpoint && (
                              <span className="ml-2 inline-flex items-center gap-1 text-[11px] text-muted-foreground" title="Money reached a shop flagged by QR Shield">
                                <QrCode className="size-3" /> QR
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-2">
                              <div className="h-1 w-12 rounded-full bg-muted">
                                <div className="h-full rounded-full bg-foreground" style={{ width: `${c.score * 100}%` }} />
                              </div>
                              <span className="num font-mono text-xs">{c.score.toFixed(2)}</span>
                            </div>
                          </td>
                          {detailed && <td className="num px-3 py-3 font-mono">{c.n_alerts}</td>}
                          <td className="num px-3 py-3 font-mono">{c.victims}</td>
                          {detailed && (
                            <td className="num px-3 py-3 font-mono text-muted-foreground">
                              {c.wallets} · {c.merchants} · {c.agents}
                            </td>
                          )}
                          <td className="num px-3 py-3 text-right font-mono">{tk(c.amount_at_risk_bdt)}</td>
                          <td className="px-3 py-3">
                            <DeadlineBar d={c.next_deadline} compact />
                          </td>
                          <td className="px-5 py-3">
                            <StatusPill status={c.status} />
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <p className="flex items-center gap-1 text-sm text-muted-foreground">
                Start with the golden thread:
                <Link href="/ops/cases/CASE-0001" className="inline-flex items-center gap-1 font-medium text-foreground underline-offset-4 hover:underline">
                  CASE-0001, the ring behind Rina&apos;s prize scam <ArrowUpRight className="size-3.5" />
                </Link>
              </p>
            </div>
          );
        }}
      </Guard>
    </div>
  );
}
