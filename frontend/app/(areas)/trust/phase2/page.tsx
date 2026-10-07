"use client";

import Link from "next/link";
import { ArrowRight, Quote } from "lucide-react";
import { useEffect, useState } from "react";
import { AreaIntro } from "@/components/customer/phone";
import { EvidenceBlock, type EvidenceFile } from "@/components/trust/phase2";
import { studyToEvidence, type StudySummary } from "@/components/study/results";
import { fetchStudy, storedPin } from "@/lib/study";
import { cn } from "@/lib/utils";

type Criterion = {
  id: string;
  name: string;
  score: number;
  max: number;
  concern: { text: string; quote: boolean } | null;
  built: string[];
  evidence: string[]; // "file" or "file#section"
};

const FILES = ["robustness", "ablation", "business", "fairness", "scalability", "security", "study", "evidence", "adversarial"] as const;
type FileName = (typeof FILES)[number];

/** Used when public/data/phase2/criteria.json is missing; the JSON file (same shape) wins when present. */
const DEFAULT_CRITERIA: Criterion[] = [
  {
    id: "problem",
    name: "Problem relevance",
    score: 17.33,
    max: 20,
    concern: { text: "no evidence of interviews, deployment observations ... controlled customer testing", quote: true },
    built: ["An on-site user study on participants' own phones, in Bangla and English: do people understand the Pause and the “not sure” state, and would they stop?"],
    evidence: ["study"],
  },
  { id: "ai_ml", name: "AI/ML depth", score: 17.0, max: 20, concern: null, built: [], evidence: ["robustness", "ablation#ladder"] },
  {
    id: "business",
    name: "Business impact",
    score: 13.33,
    max: 20,
    concern: { text: "Customer impact depends on an assumed 30–70% intervention rate.", quote: false },
    built: ["An economic model that asks what follow rate UVERA needs to break even, instead of assuming one."],
    evidence: ["business"],
  },
  { id: "prototype", name: "Prototype", score: 12, max: 15, concern: null, built: [], evidence: ["ablation#closed_loop"] },
  {
    id: "innovation",
    name: "Innovation",
    score: 7.67,
    max: 10,
    concern: { text: "quantify whether linking and evidence generation actually improve analyst decisions beyond simple alert aggregation", quote: true },
    built: ["Case Linker against naive alert aggregation on the same alerts, plus an A/B analyst task in the user study."],
    evidence: ["ablation#linking_vs_naive", "study#triage"],
  },
  { id: "scalability", name: "Scalability", score: 5.67, max: 10, concern: null, built: [], evidence: ["scalability"] },
  { id: "responsible", name: "Responsible AI", score: 3.67, max: 5, concern: null, built: [], evidence: ["fairness", "security"] },
];

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default function Phase2Page() {
  const [criteria, setCriteria] = useState<Criterion[]>(DEFAULT_CRITERIA);
  const [files, setFiles] = useState<Partial<Record<FileName, EvidenceFile | null>>>({});
  const [liveStudy, setLiveStudy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const c = await getJson<{ criteria: Criterion[] }>("/data/phase2/criteria.json");
      if (!cancelled && Array.isArray(c?.criteria) && c.criteria.length) setCriteria(c.criteria);
      const loaded = await Promise.all(FILES.map(async (f) => [f, await getJson<EvidenceFile>(`/data/phase2/${f}.json`)] as const));
      const out: Partial<Record<FileName, EvidenceFile | null>> = Object.fromEntries(loaded);
      // No measured study file yet: use the live results if the team PIN was entered in this tab.
      const pin = storedPin();
      if (out.study?.status !== "measured" && pin) {
        try {
          const res = await fetchStudy("/study/results", pin);
          if (res.ok) {
            out.study = studyToEvidence((await res.json()).summary as StudySummary);
            if (!cancelled) setLiveStudy(true);
          }
        } catch {
          /* offline: keep the file */
        }
      }
      if (!cancelled) setFiles(out);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const total = criteria.reduce((s, c) => s + c.score, 0);
  const max = criteria.reduce((s, c) => s + c.max, 0);

  return (
    <div className="mx-auto max-w-[1760px] px-4 py-8 md:px-8 xl:px-12 md:py-12">
      <AreaIntro
        label="Trust Center · Phase 2 evidence"
        title={
          <>
            What we changed <span className="italic">after Phase 1</span>.
          </>
        }
        text="For each judging criterion: the judges' main concern, what we built in response, and the measured result. Numbers are read from result files written by the Phase 2 scripts; anything not yet measured says so."
      />
      <div className="mt-6 flex flex-wrap gap-2 text-sm">
        <Link href="/trust" className="rounded-full border border-border px-4 py-2 text-muted-foreground hover:text-foreground">
          ← Trust Center
        </Link>
        <Link href="/study/results" className="inline-flex items-center gap-1.5 rounded-full border border-border px-4 py-2 hover:border-foreground/40">
          Live user study results <ArrowRight className="size-3.5" />
        </Link>
      </div>

      <section className="mt-10 rounded-2xl border border-border p-5 md:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="font-medium">Phase 1 scores</p>
          <p className="num font-mono text-sm text-muted-foreground">
            total {total.toFixed(2)} / {max}
          </p>
        </div>
        <div className="mt-4 space-y-2.5">
          {criteria.map((c) => (
            <a key={c.id} href={`#${c.id}`} className="grid grid-cols-[minmax(0,9rem)_1fr_5.5rem] items-center gap-3 text-sm hover:opacity-80 sm:grid-cols-[minmax(0,12rem)_1fr_6rem]">
              <span className="truncate">{c.name}</span>
              <span className="h-2 rounded-full bg-muted">
                <span className="block h-full rounded-full bg-foreground/70" style={{ width: `${(c.score / c.max) * 100}%` }} />
              </span>
              <span className="num text-right font-mono text-xs">
                {c.score} / {c.max}
              </span>
            </a>
          ))}
        </div>
        <p className="mt-3 text-xs text-faint">Bar = share of the points available for that criterion.</p>
      </section>

      {criteria.map((c, i) => (
        <section key={c.id} id={c.id} className="scroll-mt-24 border-t border-border py-12 first-of-type:mt-12">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <p className="label-mono">
                Criterion {i + 1} of {criteria.length}
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight">{c.name}</h2>
            </div>
            <span className="num rounded-full border border-border px-3 py-1 font-mono text-xs">
              Phase 1: {c.score} / {c.max}
            </span>
          </div>
          <div className="mt-6 grid gap-8 lg:grid-cols-[minmax(0,22rem)_1fr]">
            <div className="space-y-6">
              <div>
                <p className="label-mono">The judges&apos; concern</p>
                {c.concern && !/^\s*TBD/i.test(c.concern.text) ? (
                  <blockquote className="mt-2 flex gap-2 text-lg leading-snug">
                    <Quote className="mt-1 size-4 shrink-0 text-faint" aria-hidden="true" />
                    <span>{c.concern.quote ? <>&ldquo;{c.concern.text}&rdquo;</> : c.concern.text}</span>
                  </blockquote>
                ) : (
                  <p className="mt-2 text-sm text-faint">To be added from the Phase 1 feedback.</p>
                )}
              </div>
              <div>
                <p className="label-mono">What we built</p>
                {c.built.filter((b) => !/^\s*TBD/i.test(b)).length ? (
                  <ul className="mt-2 space-y-2 text-sm">
                    {c.built
                      .filter((b) => !/^\s*TBD/i.test(b))
                      .map((b, j) => (
                        <li key={j} className="flex gap-2">
                          <span className="mt-2 size-1.5 shrink-0 rounded-full bg-foreground/60" />
                          {b}
                        </li>
                      ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-faint">Being written up.</p>
                )}
              </div>
            </div>
            <div className="space-y-8">
              {c.evidence.map((ref) => {
                const [name, section] = ref.split("#");
                const file = files[name as FileName];
                return (
                  <EvidenceBlock
                    key={ref}
                    name={name}
                    sectionId={section}
                    file={file === undefined ? null : file}
                    extra={
                      name === "study" ? (
                        <p className={cn("text-xs", liveStudy ? "text-muted-foreground" : "text-faint")}>
                          {liveStudy ? "Shown live from the study API. " : ""}
                          <Link href="/study/results" className="underline underline-offset-4">
                            Open the live study results
                          </Link>
                        </p>
                      ) : null
                    }
                  />
                );
              })}
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}
