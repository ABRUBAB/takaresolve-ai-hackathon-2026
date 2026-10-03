"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronLeft, Info, Loader2, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { CaseGraph } from "@/components/ops/case-graph";
import { DeadlineRing, StatusPill } from "@/components/ops/bits";
import { Guard } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { post } from "@/lib/api";
import { num, pct, tk } from "@/lib/format";
import type { CaseDetail } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const ACTIONS = [
  { id: "request_evidence", label: "Request sale evidence from shops" },
  { id: "approve_hold", label: "Approve a temporary hold" },
  { id: "escalate", label: "Escalate to the fraud team" },
  { id: "dismiss", label: "Dismiss (no fraud)" },
  { id: "close", label: "Close the case" },
  { id: "note", label: "Add a note" },
] as const;

const PANELS = [
  { id: "brief", label: "Brief" },
  { id: "evidence", label: "Evidence" },
  { id: "clock", label: "Clock" },
  { id: "decide", label: "Decide" },
] as const;

export default function CaseDetailPage() {
  const { key } = useParams<{ key: string }>();
  const q = useApi<CaseDetail>(`/cases/${key}`, "ops");
  const [lang, setLang] = useState<"en" | "bn">("en");
  const [action, setAction] = useState<string>("request_evidence");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [panel, setPanel] = useState<(typeof PANELS)[number]["id"]>("brief");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim().length < 10) return toast.error("Please write a reason of at least 10 characters. Every decision is audited.");
    setSaving(true);
    try {
      const out = await post<{ message: string }>(`/cases/${key}/actions`, "ops", { action, reason: reason.trim() });
      toast.success(out.message);
      setReason("");
      q.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1760px] px-4 py-8 md:px-8 xl:px-12 md:py-10">
      <Link href="/ops" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ChevronLeft className="size-4" /> Case queue
      </Link>
      <Guard q={q}>
        {(c) => (
          <div className="mt-4 space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="label-mono">Linked case · AI-6</p>
                <h1 className="mt-2 font-mono text-4xl font-semibold tracking-tight">{c.case_key}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <StatusPill status={c.status} />
                  <span>opened {Math.round(c.opened_hours_ago / 24)} days ago</span>
                  <span>·</span>
                  <span>last complaint {Math.round(c.latest_complaint_hours_ago)} h ago</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  ["Case score", c.score.toFixed(2)],
                  ["Alerts joined", num(c.n_alerts)],
                  ["Victims", num(c.victims)],
                  ["Money at risk", tk(c.amount_at_risk_bdt)],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-2xl border border-border bg-card px-4 py-3">
                    <p className="text-[11px] text-muted-foreground">{k}</p>
                    <p className="num font-mono text-lg font-semibold">{v}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
              <section className="overflow-hidden rounded-3xl border border-border bg-card">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3">
                  <p className="text-sm font-medium">
                    Money paths · {c.wallets} wallets · {c.merchants} shops · {c.agents} agents
                  </p>
                  <span className="font-mono text-[11px] text-faint">time-ordered · ≤ 3 hops · ≤ 48 h</span>
                </div>
                <CaseGraph nodes={c.graph.nodes} edges={c.graph.edges} />
              </section>

              <section className="overflow-hidden rounded-3xl border border-border bg-card lg:sticky lg:top-20">
                <div className="no-scrollbar flex gap-1 overflow-x-auto border-b border-border p-2" role="tablist" aria-label="Case panels">
                  {PANELS.map((p) => (
                    <button
                      key={p.id}
                      role="tab"
                      aria-selected={panel === p.id}
                      onClick={() => setPanel(p.id)}
                      className={cn("h-9 shrink-0 rounded-full px-4 text-sm", panel === p.id ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground")}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <div className="p-5">
                  {panel === "brief" && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <OutputChip type="generated">{`Generated · ${c.brief.source.replace("_", " ")}`}</OutputChip>
                        <div className="flex rounded-full border border-border p-0.5 text-[11px]">
                          {(["en", "bn"] as const).map((l) => (
                            <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l} className={cn("rounded-full px-2 py-0.5", lang === l ? "bg-foreground text-background" : "text-muted-foreground")}>
                              {l === "en" ? "EN" : "বাং"}
                            </button>
                          ))}
                        </div>
                      </div>
                  <p className={cn("text-sm leading-relaxed", lang === "bn" && "bn")}>{lang === "en" ? c.brief.english : c.brief.bangla}</p>
                  <p className="mt-3 flex gap-1.5 text-xs text-muted-foreground">
                    <ShieldCheck className="mt-0.5 size-3.5 shrink-0" />
                    Uses only evidence {c.brief.evidence_ids.join(", ")} and cards {c.brief.card_ids.join(", ")}. A validator rejects any new number, link or instruction.
                  </p>
                    </div>
                  )}
                  {panel === "evidence" && (
                    <div className="space-y-4">
                      <p className="text-xs text-muted-foreground">{pct(c.forwarded_share)} of the money moved on within 48 h</p>
                  <ol className="space-y-3">
                    {c.evidence.map((e) => (
                      <li key={e.id} className="flex items-start gap-3">
                        <span className="num mt-0.5 font-mono text-xs text-faint">{e.id}</span>
                        <p className="flex-1 text-sm">{e.text}</p>
                        <OutputChip type={e.type === "rule" ? "rule" : "model"} />
                      </li>
                    ))}
                  </ol>
                    </div>
                  )}
                  {panel === "clock" && (
                    <div>
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium">Dispute clock</p>
                        <OutputChip type="rule" />
                      </div>
                      <div className="mt-5 grid grid-cols-2 gap-5">
                        {c.dispute_clock.map((d) => (
                          <DeadlineRing key={d.rule} d={d} />
                        ))}
                      </div>
                      {!c.dispute_rules_verified && (
                        <p className="mt-5 flex gap-1.5 text-xs text-muted-foreground">
                          <Info className="mt-0.5 size-3.5 shrink-0" />
                          {c.dispute_rules_note}
                        </p>
                      )}
                    </div>
                  )}
                  {panel === "decide" && (
                    <div>
                  <p className="mt-1 text-xs text-muted-foreground">The AI only recommends. A person makes and signs every decision.</p>
                  <form onSubmit={submit} className="mt-4 space-y-3">
                    <select value={action} onChange={(e) => setAction(e.target.value)} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm">
                      {ACTIONS.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.label}
                        </option>
                      ))}
                    </select>
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      rows={3}
                      maxLength={500}
                      placeholder="Reason (required, at least 10 characters)"
                      className="w-full rounded-xl border border-border bg-background p-3 text-sm"
                    />
                    <button disabled={saving} className="flex h-10 w-full items-center justify-center gap-2 rounded-full bg-foreground text-sm font-medium text-background disabled:opacity-50">
                      {saving && <Loader2 className="size-4 animate-spin" />}
                      Record decision
                    </button>
                  </form>
                  {c.actions.length > 0 && (
                    <div className="mt-5 border-t border-border pt-4">
                      <p className="label-mono mb-2">Audit log</p>
                      <ul className="space-y-2 text-sm">
                        {c.actions.map((a, i) => (
                          <li key={i}>
                            <p>
                              <span className="font-medium">{a.action.replace(/_/g, " ")}</span>
                              <span className="text-faint"> · {a.actor_id} · {new Date(a.at * 1000).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" })}</span>
                            </p>
                            <p className="text-muted-foreground">{a.reason}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                    </div>
                  )}
                </div>
              </section>
            </div>
            <p className="font-mono text-[11px] text-faint">
              trace {c.trace_id} · model {c.model_version} · data {c.data_version}
            </p>
          </div>
        )}
      </Guard>
    </div>
  );
}
