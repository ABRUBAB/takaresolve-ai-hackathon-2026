"use client";

import { useSearchParams } from "next/navigation";
import { ChevronDown, Info } from "lucide-react";
import { Suspense, useState } from "react";
import { AreaIntro } from "@/components/customer/phone";
import { QrBadge } from "@/components/ops/bits";
import { Guard } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { ReasonList } from "@/components/trust/evidence";
import { KV } from "@/components/trust/inspector";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { num, pct, tk } from "@/lib/format";
import type { QrDetail, QrList, QrState } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import { TapHint } from "@/components/ui/tap-hint";

const FILTERS: { id: QrState | "all"; label: string }[] = [
  { id: "all", label: "All flagged" },
  { id: "red", label: "Review now" },
  { id: "amber", label: "Watch" },
  { id: "grey_review", label: "Not sure" },
];

function MerchantDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const q = useApi<QrDetail>(id ? `/qr/merchants/${id}` : null, "ops");
  return (
    <Sheet open={!!id} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="font-mono">{id}</SheetTitle>
          <SheetDescription>QR Shield · merchant-week review</SheetDescription>
        </SheetHeader>
        <div className="space-y-6 px-4 pb-8">
          <Guard q={q}>
            {(m) => (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <QrBadge state={m.state} />
                  <span className="text-sm text-muted-foreground">
                    {m.category.replace(/_/g, " ")} · {m.zone.replace(/_/g, "-")} · {m.size} · week {m.week}
                  </span>
                </div>
                <KV
                  rows={[
                    ["Calibrated chance of hidden cash-out", pct(m.p_calibrated)],
                    ["Payments this week", num(m.payments)],
                    ["QR volume this week", tk(m.volume_bdt)],
                    ["Estimated fee leakage", tk(m.est_fee_leakage_bdt)],
                  ]}
                />
                <section className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="label-mono">Why it was flagged</h3>
                    <OutputChip type="model">TreeSHAP</OutputChip>
                  </div>
                  <ReasonList reasons={m.reasons} />
                </section>
                <section className="space-y-3">
                  <h3 className="label-mono">Compared with {m.peers_n} shops of the same type, area and size</h3>
                  <div className="overflow-hidden rounded-2xl border border-border">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 font-normal">Signal</th>
                          <th className="px-3 py-2 text-right font-normal">This shop</th>
                          <th className="px-3 py-2 text-right font-normal">Peer median</th>
                          <th className="px-3 py-2 text-right font-normal">Peer 90th</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {m.peer_comparison.map((p) => (
                          <tr key={p.metric} className={cn(p.this_shop > p.peer_p90 && "bg-risk/5")}>
                            <td className="px-3 py-2">{p.metric}</td>
                            <td className="num px-3 py-2 text-right font-mono">{num(p.this_shop, 2)}</td>
                            <td className="num px-3 py-2 text-right font-mono text-muted-foreground">{num(p.peer_median, 2)}</td>
                            <td className="num px-3 py-2 text-right font-mono text-muted-foreground">{num(p.peer_p90, 2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
                <section className="space-y-3">
                  <h3 className="label-mono">Three detectors (rank 0–1)</h3>
                  {(
                    [
                      ["Supervised model (70%)", m.components.supervised],
                      ["Isolation Forest (30%)", m.components.isolation_forest],
                      ["Peer z-score (baseline, not in the fusion)", m.components.peer_z],
                    ] as [string, number][]
                  ).map(([k, v]) => (
                    <div key={k} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>{k}</span>
                        <span className="num font-mono">{v.toFixed(2)}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted">
                        <div className="h-full rounded-full bg-foreground/70" style={{ width: `${v * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </section>
                <section className="space-y-2">
                  <h3 className="label-mono">Weeks</h3>
                  <div className="flex gap-2">
                    {m.history.map((h) => (
                      <div key={h.week} className="flex-1 rounded-xl border border-border p-2 text-center">
                        <p className="text-[11px] text-faint">wk {h.week}</p>
                        <div className="mt-1 flex justify-center">
                          <QrBadge state={h.state} />
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="label-mono">Suggested next steps</h3>
                    <OutputChip type="rule" />
                  </div>
                  <ul className="list-disc space-y-1 pl-5 text-sm">
                    {m.recommended_actions.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                </section>
                <p className="flex gap-1.5 rounded-2xl border border-dashed border-border p-3 text-xs text-muted-foreground">
                  <Info className="mt-0.5 size-3.5 shrink-0" />
                  Fee leakage is an estimate: suspected QR volume × an assumed cash-out fee. {m.fee_assumption.note}
                </p>
              </>
            )}
          </Guard>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Watchlist() {
  const params = useSearchParams();
  const [filter, setFilter] = useState<QrState | "all">("all");
  const [open, setOpen] = useState<string | null>(params.get("merchant"));
  const [showAll, setShowAll] = useState(false);
  const q = useApi<QrList>(`/qr/merchants?limit=120${filter === "all" ? "" : `&state=${filter}`}`, "ops");

  return (
    <div className="mx-auto max-w-[1760px] px-4 py-8 md:px-8 xl:px-12 md:py-12">
      <AreaIntro
        label="Operations · AI-5 QR Shield"
        title={
          <>
            Shops used as a <span className="italic">hidden cash machine</span>.
          </>
        }
        text="Some merchant QR codes are used to take cash out without the cash-out fee: round payments, quick bursts, payers emptying their wallet right after a cash-in. Each shop is compared with shops of the same type, area and size, so small honest shops are not over-flagged."
      />
      <Guard q={q}>
        {(d) => {
          const flagged = d.merchants.filter((m) => m.state !== "green");
          const rows = showAll ? flagged : flagged.slice(0, 20);
          const shopType = (m: (typeof flagged)[number]) => `${m.category.replace(/_/g, " ")} · ${m.zone.replace(/_/g, "-")} · ${m.size}`;
          return (
            <div className="mt-10 space-y-6">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {[
                  ["Review now", d.counts.red ?? 0],
                  ["Watch", d.counts.amber ?? 0],
                  ["Not sure · person checks", d.counts.grey_review ?? 0],
                  ["Normal", d.counts.green ?? 0],
                ].map(([k, v]) => (
                  <div key={String(k)} className="rounded-2xl border border-border bg-card p-4">
                    <p className="text-xs text-muted-foreground">{k}</p>
                    <p className="num mt-1 font-mono text-xl font-semibold md:text-2xl">{num(Number(v))}</p>
                  </div>
                ))}
                <div className="col-span-2 rounded-2xl border border-border bg-card p-4 sm:col-span-1">
                  <p className="text-xs text-muted-foreground">Est. fee leakage this week</p>
                  <p className="num mt-1 font-mono text-xl font-semibold md:text-2xl">{tk(d.counts.est_fee_leakage_bdt)}</p>
                  <OutputChip type="assumption" className="mt-1" />
                </div>
              </div>
              <div className="no-scrollbar flex gap-2 overflow-x-auto" role="tablist" aria-label="Filter">
                {FILTERS.map((f) => (
                  <button
                    key={f.id}
                    role="tab"
                    aria-selected={filter === f.id}
                    onClick={() => {
                      setFilter(f.id);
                      setShowAll(false);
                    }}
                    className={cn("shrink-0 rounded-full border px-3 py-1.5 text-sm", filter === f.id ? "border-foreground bg-foreground text-background" : "border-border text-muted-foreground")}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <TapHint>Tap a shop to open its file</TapHint>
              <div className="overflow-hidden rounded-3xl border border-border bg-card">
                {/* phones: one card per shop */}
                <ul className="divide-y divide-border md:hidden">
                  {rows.map((m) => (
                    <li key={m.merchant_id}>
                      <button onClick={() => setOpen(m.merchant_id)} className="block w-full space-y-1.5 px-5 py-4 text-left active:bg-muted/50">
                        <span className="flex items-center justify-between gap-2">
                          <span className="font-mono font-medium">{m.merchant_id}</span>
                          <QrBadge state={m.state} />
                        </span>
                        <span className="block text-xs text-muted-foreground">{shopType(m)}</span>
                        <span className="block text-sm">{m.reasons[0]?.text_en ?? "—"}</span>
                        <span className="num flex justify-between font-mono text-xs text-muted-foreground">
                          <span>{m.payments} payments</span>
                          <span>leakage {tk(m.est_fee_leakage_bdt)}</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
                <div className="hidden overflow-x-auto md:block">
                  <table className="w-full min-w-[820px] text-sm">
                    <thead className="text-left text-xs text-muted-foreground">
                      <tr className="border-b border-border">
                        <th className="px-5 py-2.5 font-normal">Shop</th>
                        <th className="px-3 py-2.5 font-normal">State</th>
                        <th className="px-3 py-2.5 font-normal">Type · area · size</th>
                        <th className="px-3 py-2.5 font-normal">Top reason</th>
                        <th className="px-3 py-2.5 text-right font-normal">Payments</th>
                        <th className="px-5 py-2.5 text-right font-normal">Fee leakage</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {rows.map((m) => (
                        <tr key={m.merchant_id} onClick={() => setOpen(m.merchant_id)} className="cursor-pointer hover:bg-muted/50">
                          <td className="px-5 py-3">
                            <button className="font-mono font-medium hover:underline" onClick={() => setOpen(m.merchant_id)}>
                              {m.merchant_id}
                            </button>
                          </td>
                          <td className="px-3 py-3">
                            <QrBadge state={m.state} />
                          </td>
                          <td className="px-3 py-3 text-muted-foreground">{shopType(m)}</td>
                          <td className="max-w-80 px-3 py-3">
                            <span className="line-clamp-2">{m.reasons[0]?.text_en ?? "—"}</span>
                          </td>
                          <td className="num px-3 py-3 text-right font-mono">{m.payments}</td>
                          <td className="num px-5 py-3 text-right font-mono">{tk(m.est_fee_leakage_bdt)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {rows.length === 0 && <p className="p-6 text-sm text-muted-foreground">No shops in this state this week.</p>}
              </div>
              {flagged.length > 20 && (
                <button
                  onClick={() => setShowAll((v) => !v)}
                  aria-expanded={showAll}
                  className="mx-auto flex h-11 items-center gap-2 rounded-full border border-border px-5 text-sm hover:border-foreground/40"
                >
                  {showAll ? "Show the first 20 only" : `Show all ${flagged.length} flagged shops`}
                  <ChevronDown className={cn("size-4 transition-transform", showAll && "rotate-180")} />
                </button>
              )}
              <p className="text-sm text-muted-foreground">
                “Review now” = a higher score than 98% of honest shop-weeks in the validation weeks; “Watch” = higher than 90%. The calibrated
                probability is shown inside each shop. Analysts review about 20 shops a week.
              </p>
            </div>
          );
        }}
      </Guard>
      <MerchantDrawer id={open} onClose={() => setOpen(null)} />
    </div>
  );
}

export default function QrPage() {
  return (
    <Suspense>
      <Watchlist />
    </Suspense>
  );
}
