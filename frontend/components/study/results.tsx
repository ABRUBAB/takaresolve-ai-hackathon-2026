"use client";

import Link from "next/link";
import { ArrowRight, Download, Lock, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Mark } from "@/components/brand/logo";
import { API_BASE } from "@/lib/api";
import { fetchStudy, storedPin, storePin } from "@/lib/study";
import { cn } from "@/lib/utils";
import type { EvidenceFile } from "@/components/trust/phase2";

type Rate = { k: number; n: number; rate: number | null; ci95: [number, number] | null };
type Mean = { n: number; mean: number | null; sd: number | null };
type Arm = {
  n: number;
  rings_correct: Rate;
  wallet_correct: Rate;
  both_correct: Rate;
  median_time_s: number | null;
  times_s: number[];
  wallets: Record<string, number>;
  rings_answers: Record<string, number>;
  confidence: Mean;
};
export type StudySummary = {
  n: number;
  first_at: string | null;
  last_at: string | null;
  facilitators: Record<string, number>;
  profile: Record<string, Record<string, number>>;
  task1: {
    n: number;
    comprehension: Rate & { by_lang: Record<"bn" | "en", Rate> };
    stated_stop: Rate & { by_lang: Record<"bn" | "en", Rate> };
    meaning: Record<string, number>;
    actions: Record<string, number>;
    reasons: Record<string, number>;
    clarity: Mean;
    trust: Mean;
    annoyance: Mean;
    median_view_s: number | null;
  };
  task2: { n: number; understood: Rate; answers: Record<string, number>; ok_unsure: Mean };
  task3: Record<"A" | "B", Arm>;
  comments: string[];
  caveat: string;
};

const pc = (r?: number | null) => (r == null ? "—" : `${Math.round(r * 100)}%`);
const ci = (r: Rate) => (r.ci95 ? `95% CI ${Math.round(r.ci95[0] * 100)}–${Math.round(r.ci95[1] * 100)}%` : "no answers yet");

const LABELS: Record<string, string> = {
  wait: "Wait 10 minutes",
  verify: "Verify the number",
  ask: "Ask someone I trust",
  send_anyway: "Send anyway",
  senders: "19 people paid them this week",
  moves_on: ">99% of money moves on",
  wallet_age: "12-day-old receiver wallet",
  none: "None of them",
  paused_scam: "May be a scam, paused (correct)",
  failed: "Transfer failed",
  blocked: "Account blocked",
  not_sure: "Not sure",
  person_checks: "A person checks first (correct)",
  sent: "Money is sent",
  lost: "Money is lost",
};

const PROFILE_LABELS: Record<string, string> = { bn: "Bangla", en: "English", both: "Both", prefer_not: "Prefer not to say", not_sure: "Not sure", no_answer: "No answer" };

/** The study aggregate in the Phase 2 evidence-file shape (public/data/phase2/README.md): used live by /trust/phase2 and
 * downloaded from this page as a ready-to-use study.json. */
export function studyToEvidence(s: StudySummary): EvidenceFile {
  const A = s.task3.A;
  const B = s.task3.B;
  const sub = (r: { k: number; n: number; ci95: [number, number] | null }) =>
    `${r.k} of ${r.n}${r.ci95 ? ` · 95% CI ${Math.round(r.ci95[0] * 100)}–${Math.round(r.ci95[1] * 100)}%` : ""}`;
  return {
    status: s.n > 0 ? "measured" : "pending",
    title: "On-site user study (live)",
    updated_at: s.last_at,
    source: "Live from the API: /v1/study/results (anonymous responses from /study)",
    summary: "Volunteers at the venue, on their own phones. Small n: a quick usability study, not a representative survey; answers are stated intentions.",
    headline: [
      { label: "participants", value: s.n, format: "num" },
      { label: "understood the Pause screen", value: s.task1.comprehension.rate, format: "pct", sub: sub(s.task1.comprehension) },
      { label: "would not send anyway (stated stop rate)", value: s.task1.stated_stop.rate, format: "pct", sub: sub(s.task1.stated_stop) },
      { label: "understood “not sure”: a person checks", value: s.task2.understood.rate, format: "pct", sub: sub(s.task2.understood) },
    ],
    sections: [
      {
        id: "triage",
        title: "Analyst task: plain alert list (A) vs linked cases (B)",
        lead: `Same 12 alerts, 3 hidden rings. n = ${A.n} (A) and ${B.n} (B). Median time to answer: A ${A.median_time_s ?? "—"} s, B ${B.median_time_s ?? "—"} s.`,
        chart: {
          kind: "bars",
          unit: "pct",
          x: ["Both answers correct", "Rings counted correctly (3)", "Right wallet first (W-77)"],
          series: [
            { name: "A · alert list", values: [A.both_correct.rate, A.rings_correct.rate, A.wallet_correct.rate] },
            { name: "B · linked cases", values: [B.both_correct.rate, B.rings_correct.rate, B.wallet_correct.rate] },
          ],
        },
      },
      {
        id: "ratings",
        title: "Ratings (mean, 1–5)",
        chart: {
          kind: "bars",
          unit: "num",
          x: ["Pause screen is clear", "Would trust the warning", "Annoying if the transfer was safe", "OK to say “not sure”"],
          series: [{ name: "mean", values: [s.task1.clarity.mean, s.task1.trust.mean, s.task1.annoyance.mean, s.task2.ok_unsure.mean] }],
        },
      },
    ],
  };
}

export function StudyResults() {
  const [pin, setPin] = useState(storedPin);
  const [draft, setDraft] = useState("");
  const [data, setData] = useState<{ summary: StudySummary; generated_at: string } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (p: string) => {
    if (!p) return;
    setBusy(true);
    try {
      const res = await fetchStudy("/study/results", p);
      if (res.status === 401 || res.status === 403) {
        storePin(null);
        setPin("");
        setError("That PIN did not work.");
        return;
      }
      if (!res.ok) throw new Error(`The API answered ${res.status}.`);
      setData(await res.json());
      setError("");
    } catch (e) {
      setError(e instanceof Error && e.message !== "Failed to fetch" ? e.message : "The live API is not reachable right now.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!pin) return;
    const first = setTimeout(() => load(pin), 0);
    const id = setInterval(() => load(pin), 15000);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [pin, load]);

  const downloadCsv = async () => {
    const res = await fetchStudy("/study/export.csv", pin);
    if (!res.ok) return setError(`CSV export failed (${res.status}).`);
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = "uvera_study_responses.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  /** study.json for public/data/phase2: the evidence-file shape plus the full aggregate (no free-text comments, no rows). */
  const downloadJson = () => {
    if (!data) return;
    const file = {
      ...studyToEvidence(data.summary),
      title: "On-site user study",
      updated_at: data.generated_at,
      source: `Exported from /v1/study/results at ${data.generated_at} (anonymous responses from /study)`,
      aggregate: { ...data.summary, comments: undefined },
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(file, null, 2) + "\n"], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "study.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <div className="mx-auto max-w-[1280px] px-4 pb-16 md:px-8">
      <header className="flex h-14 items-center gap-3 border-b border-border">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-[-0.03em]">
          <Mark /> UVERA
        </Link>
        <span className="label-mono hidden sm:inline">User study · live results</span>
        <nav className="ml-auto flex items-center gap-1 text-sm">
          <Link href="/trust" className="rounded-full px-3 py-1.5 text-muted-foreground hover:text-foreground">
            Trust Center
          </Link>
          <Link href="/trust/phase2" className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 hover:border-foreground/40">
            Phase 2 evidence <ArrowRight className="size-3.5" />
          </Link>
        </nav>
      </header>

      <div className="py-8 md:py-12">
        <p className="label-mono">On-site user study · {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</p>
        <h1 className="mt-3 font-serif text-4xl leading-[1.05] md:text-6xl">
          Do people understand the pause, <span className="italic">and does linking help analysts?</span>
        </h1>
        <p className="mt-4 max-w-3xl text-muted-foreground">
          Volunteers at the venue used the study page on their own phones: two warning screens (the Pause and the “not sure” state, shown in
          Bangla or English at random) and an analyst task where half saw a plain alert list (A) and half saw the same alerts linked into cases (B).
        </p>
        <p className="mt-4 inline-flex rounded-xl border border-dashed border-caution/60 px-3 py-2 text-sm">
          n is small; this is a quick on-site usability study, not a representative survey. Answers are stated intentions, not observed behaviour.
        </p>
      </div>

      {!pin ? (
        <form
          className="max-w-sm space-y-3 rounded-2xl border border-border p-5"
          onSubmit={(e) => {
            e.preventDefault();
            const v = draft.trim();
            if (!v) return;
            storePin(v);
            setPin(v);
            setDraft("");
          }}
        >
          <p className="flex items-center gap-2 font-medium">
            <Lock className="size-4" /> Team PIN
          </p>
          <input
            type="password"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoComplete="off"
            className="h-12 w-full rounded-xl border border-border bg-background px-3 font-mono"
            aria-label="Study PIN"
          />
          <button type="submit" className="h-11 w-full rounded-full bg-foreground font-medium text-background">
            Show results
          </button>
          {error && <p className="text-sm text-risk">{error}</p>}
          {!API_BASE && <p className="text-sm text-muted-foreground">No live API is configured for this build.</p>}
        </form>
      ) : (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-2 text-sm">
            <span className="label-mono">{data ? `Updated ${new Date(data.generated_at).toLocaleTimeString("en-GB")} · refreshes every 15 s` : "Loading…"}</span>
            <button onClick={() => load(pin)} className="ml-auto inline-flex h-9 items-center gap-1.5 rounded-full border border-border px-3 text-muted-foreground hover:text-foreground">
              <RefreshCw className={cn("size-3.5", busy && "animate-spin")} /> Refresh
            </button>
            <button onClick={downloadCsv} className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border px-3 text-muted-foreground hover:text-foreground">
              <Download className="size-3.5" /> CSV
            </button>
            <button
              onClick={downloadJson}
              disabled={!data}
              title="Aggregate in the Phase 2 study.json format"
              className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border px-3 text-muted-foreground hover:text-foreground disabled:opacity-40"
            >
              <Download className="size-3.5" /> Download JSON
            </button>
            <button
              onClick={() => {
                storePin(null);
                setPin("");
                setData(null);
              }}
              className="h-9 rounded-full px-3 text-muted-foreground hover:text-foreground"
            >
              Lock
            </button>
          </div>
          {error && <p className="mb-6 rounded-xl border border-border p-3 text-sm text-muted-foreground">{error}</p>}
          {data && <Dashboard s={data.summary} />}
        </>
      )}
    </div>
  );
}

function Dashboard({ s }: { s: StudySummary }) {
  const t1 = s.task1;
  const A = s.task3.A;
  const B = s.task3.B;
  return (
    <div className="space-y-12">
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi big={`${s.n}`} label="participants" sub={s.last_at ? `last response ${new Date(s.last_at).toLocaleTimeString("en-GB")}` : "waiting for the first response"} />
        <Kpi big={pc(t1.comprehension.rate)} label="understood the Pause screen" sub={`${t1.comprehension.k} of ${t1.comprehension.n} · ${ci(t1.comprehension)}`} accent />
        <Kpi big={pc(t1.stated_stop.rate)} label="would not send anyway (stated stop rate)" sub={`${t1.stated_stop.k} of ${t1.stated_stop.n} · ${ci(t1.stated_stop)}`} />
        <Kpi big={pc(s.task2.understood.rate)} label="understood “not sure”: a person checks" sub={`${s.task2.understood.k} of ${s.task2.understood.n} · ${ci(s.task2.understood)}`} />
      </section>

      <Block title="Task 3 · Analyst triage: plain list (A) vs linked cases (B)" lead="Same 12 synthetic alerts, 3 hidden rings + 1 single alert. Correct: 3 rings, check W-77 first (5 victims). Between-subject, randomly assigned.">
        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <div className="space-y-5 rounded-2xl border border-border p-5">
            <PairBars
              title="Both answers correct"
              rows={[
                ["A · alert list", A.both_correct.rate, `${A.both_correct.k}/${A.both_correct.n}`],
                ["B · linked cases", B.both_correct.rate, `${B.both_correct.k}/${B.both_correct.n}`],
              ]}
            />
            <PairBars
              title="Rings counted correctly (3)"
              rows={[
                ["A · alert list", A.rings_correct.rate, `${A.rings_correct.k}/${A.rings_correct.n}`],
                ["B · linked cases", B.rings_correct.rate, `${B.rings_correct.k}/${B.rings_correct.n}`],
              ]}
            />
            <PairBars
              title="Picked the right wallet (W-77)"
              rows={[
                ["A · alert list", A.wallet_correct.rate, `${A.wallet_correct.k}/${A.wallet_correct.n}`],
                ["B · linked cases", B.wallet_correct.rate, `${B.wallet_correct.k}/${B.wallet_correct.n}`],
              ]}
            />
          </div>
          <div className="space-y-5 rounded-2xl border border-border p-5">
            <div className="grid grid-cols-2 gap-3">
              <Mini label="A · median time" value={A.median_time_s != null ? `${A.median_time_s} s` : "—"} sub={`n = ${A.n}`} />
              <Mini label="B · median time" value={B.median_time_s != null ? `${B.median_time_s} s` : "—"} sub={`n = ${B.n}`} accent />
              <Mini label="A · confidence" value={A.confidence.mean != null ? `${A.confidence.mean} / 5` : "—"} />
              <Mini label="B · confidence" value={B.confidence.mean != null ? `${B.confidence.mean} / 5` : "—"} />
            </div>
            <TimeStrip a={A.times_s} b={B.times_s} />
            <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
              <Counts title="A · wallet picked" c={A.wallets} />
              <Counts title="B · wallet picked" c={B.wallets} />
            </div>
          </div>
        </div>
      </Block>

      <Block title="Task 1 · The Pause screen" lead="Prize-scam transfer of Tk 3,000, shown in Bangla or English at random.">
        <div className="grid gap-4 lg:grid-cols-3">
          <Card title="What would you do now?">
            <HBars counts={t1.actions} order={["wait", "verify", "ask", "send_anyway"]} highlight="send_anyway" />
          </Card>
          <Card title="Which reason made you most careful?">
            <HBars counts={t1.reasons} order={["senders", "moves_on", "wallet_age", "none"]} />
          </Card>
          <Card title="Ratings (1–5)">
            <div className="space-y-4">
              <Scale label="Clear" m={t1.clarity} />
              <Scale label="Would trust it" m={t1.trust} />
              <Scale label="Annoying if the transfer was safe (lower is better)" m={t1.annoyance} invert />
            </div>
            <p className="mt-4 text-xs text-muted-foreground">Median time looking at the screen: {t1.median_view_s != null ? `${t1.median_view_s} s` : "—"}</p>
          </Card>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Understood, by language of the screen">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground">
                <tr>
                  <th className="py-1 font-normal">Screen</th>
                  <th className="py-1 text-right font-normal">Understood</th>
                  <th className="py-1 text-right font-normal">Would not send</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono text-xs">
                {(["bn", "en"] as const).map((l) => (
                  <tr key={l}>
                    <td className="py-2 font-sans text-sm">{l === "bn" ? "Bangla" : "English"}</td>
                    <td className="py-2 text-right">
                      {pc(t1.comprehension.by_lang[l]?.rate)} <span className="text-faint">({t1.comprehension.by_lang[l]?.k ?? 0}/{t1.comprehension.by_lang[l]?.n ?? 0})</span>
                    </td>
                    <td className="py-2 text-right">
                      {pc(t1.stated_stop.by_lang[l]?.rate)} <span className="text-faint">({t1.stated_stop.by_lang[l]?.k ?? 0}/{t1.stated_stop.by_lang[l]?.n ?? 0})</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <Card title="What is this screen telling you?">
            <HBars counts={t1.meaning} order={["paused_scam", "failed", "blocked", "not_sure"]} />
          </Card>
        </div>
      </Block>

      <Block title="Task 2 · The “not sure” state" lead="New phone + PIN reset, Tk 9,000 at 11 pm: the model is not sure, so a person checks.">
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="What happens next?">
            <HBars counts={s.task2.answers} order={["person_checks", "sent", "lost", "not_sure"]} />
          </Card>
          <Card title="OK that the app says “not sure” instead of guessing (1–5)">
            <Scale label="Agreement" m={s.task2.ok_unsure} />
          </Card>
        </div>
      </Block>

      <Block title="Who took part" lead="Self-reported bands only. No names or phone numbers are collected.">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[
            ["Age", "age_band"],
            ["Mobile money use", "mm_use"],
            ["Phone language", "phone_lang"],
            ["Got a scam SMS/call", "scam_contact"],
            ["Lost money to a scam", "scam_loss"],
          ].map(([t, k]) => (
            <Card key={k} title={t}>
              <HBars counts={s.profile[k] ?? {}} compact />
            </Card>
          ))}
        </div>
      </Block>

      {s.comments.length > 0 && (
        <Block title="In their words" lead="Optional comments (phone numbers and e-mail addresses are removed by the server).">
          <ul className="grid gap-2 md:grid-cols-2">
            {s.comments.map((c, i) => (
              <li key={i} className="rounded-2xl border border-border p-4 text-sm">
                “{c}”
              </li>
            ))}
          </ul>
        </Block>
      )}

      <p className="border-t border-border pt-6 text-xs text-faint">{s.caveat} Screens are synthetic demos; no real money or customer data.</p>
    </div>
  );
}

function Block({ title, lead, children }: { title: string; lead?: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        {lead && <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{lead}</p>}
      </div>
      {children}
    </section>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-border p-5">
      <p className="mb-4 text-sm font-medium">{title}</p>
      {children}
    </div>
  );
}

function Kpi({ big, label, sub, accent }: { big: string; label: string; sub?: string; accent?: boolean }) {
  return (
    <div className={cn("rounded-2xl border p-5", accent ? "border-volt-ink/50 dark:border-volt/40" : "border-border")}>
      <p className="num font-mono text-5xl font-semibold tracking-tight">{big}</p>
      <p className="mt-2 text-sm">{label}</p>
      {sub && <p className="mt-1 font-mono text-[11px] text-faint">{sub}</p>}
    </div>
  );
}

function Mini({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div className={cn("rounded-xl border p-3", accent ? "border-volt-ink/50 dark:border-volt/40" : "border-border")}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="num mt-1 font-mono text-2xl font-semibold">{value}</p>
      {sub && <p className="font-mono text-[11px] text-faint">{sub}</p>}
    </div>
  );
}

function PairBars({ title, rows }: { title: string; rows: [string, number | null, string][] }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{title}</p>
      <div className="space-y-2">
        {rows.map(([k, v, n], i) => (
          <div key={k} className="grid grid-cols-[7.5rem_1fr_4.5rem] items-center gap-3 text-sm">
            <span className="text-xs text-muted-foreground">{k}</span>
            <div className="h-3 rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full transition-[width] duration-500", i === 1 ? "bg-volt-ink dark:bg-volt" : "bg-foreground/60")}
                style={{ width: `${(v ?? 0) * 100}%` }}
              />
            </div>
            <span className="num text-right font-mono text-xs">
              {pc(v)} <span className="text-faint">{n}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function HBars({ counts, order, highlight, compact }: { counts: Record<string, number>; order?: string[]; highlight?: string; compact?: boolean }) {
  const keys = order ? [...order, ...Object.keys(counts).filter((k) => !order.includes(k))] : Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const total = Object.values(counts).reduce((s, v) => s + v, 0);
  const max = Math.max(1, ...Object.values(counts));
  if (!keys.length) return <p className="text-sm text-faint">No answers yet</p>;
  return (
    <div className="space-y-2.5">
      {keys.map((k) => {
        const v = counts[k] ?? 0;
        return (
          <div key={k}>
            <div className="flex justify-between gap-2 text-xs">
              <span>{compact ? (PROFILE_LABELS[k] ?? k) : (LABELS[k] ?? k.replace(/_/g, " "))}</span>
              <span className="num font-mono text-muted-foreground">
                {v}
                {total ? ` · ${Math.round((v / total) * 100)}%` : ""}
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-muted">
              <div className={cn("h-full rounded-full", k === highlight ? "bg-risk" : "bg-foreground/70")} style={{ width: `${(v / max) * 100}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Scale({ label, m, invert }: { label: string; m: Mean; invert?: boolean }) {
  const pos = m.mean != null ? ((m.mean - 1) / 4) * 100 : null;
  return (
    <div>
      <div className="flex justify-between gap-2 text-xs">
        <span>{label}</span>
        <span className="num font-mono">
          {m.mean != null ? m.mean.toFixed(1) : "—"} <span className="text-faint">/ 5 · n {m.n}</span>
        </span>
      </div>
      <div className="relative mt-2 h-2 rounded-full bg-muted">
        {pos != null && (
          <>
            <div className={cn("absolute inset-y-0 left-0 rounded-full", invert ? "bg-foreground/30" : "bg-foreground/70")} style={{ width: `${pos}%` }} />
            <span className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-foreground" style={{ left: `${pos}%` }} />
          </>
        )}
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-faint">
        <span>1</span>
        <span>5</span>
      </div>
    </div>
  );
}

function Counts({ title, c }: { title: string; c: Record<string, number> }) {
  const keys = Object.keys(c).sort((a, b) => c[b] - c[a]);
  return (
    <div>
      <p className="mb-1">{title}</p>
      {keys.length ? (
        <ul className="space-y-0.5 font-mono">
          {keys.map((k) => (
            <li key={k} className={cn(k === "W-77" && "text-foreground")}>
              {k.replace("_", " ")} · {c[k]}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-faint">—</p>
      )}
    </div>
  );
}

/** Every participant's time to answer, one dot each, on a shared axis. */
function TimeStrip({ a, b }: { a: number[]; b: number[] }) {
  const max = Math.max(30, ...a, ...b);
  const ticks = [0, max / 2, max].map((t) => Math.round(t));
  const row = (xs: number[], label: string, accent: boolean) => (
    <div className="grid grid-cols-[5.5rem_1fr] items-center gap-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="relative h-6 rounded-full bg-muted/50">
        {xs.map((x, i) => (
          <span
            key={i}
            title={`${x} s`}
            className={cn("absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full", accent ? "bg-volt-ink dark:bg-volt" : "bg-foreground/70")}
            style={{ left: `${(x / max) * 100}%` }}
          />
        ))}
      </div>
    </div>
  );
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">Time to answer, each dot is one person</p>
      {row(a, "A · list", false)}
      {row(b, "B · cases", true)}
      <div className="ml-[6.25rem] flex justify-between font-mono text-[10px] text-faint">
        {ticks.map((t) => (
          <span key={t}>{t} s</span>
        ))}
      </div>
    </div>
  );
}
