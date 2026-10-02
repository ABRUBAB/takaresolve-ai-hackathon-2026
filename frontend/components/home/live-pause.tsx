"use client";

import Link from "next/link";
import { ArrowUpRight, Loader2, Play } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { ErrorBox } from "@/components/shell/states";
import { OutputChip, RiskBadge, riskStateOf } from "@/components/trust/chips";
import { actionText, HighlightedText, ProbabilityMeter, ReasonList, unsureText } from "@/components/trust/evidence";
import { post } from "@/lib/api";
import { tk } from "@/lib/format";
import type { Demo, PauseRequest, PauseResult } from "@/lib/types";
import { useAction, usePublic } from "@/lib/use-api";
import { cn } from "@/lib/utils";

export function LivePause() {
  const demo = usePublic<Demo>("/demo");
  const scenarios = (demo.data?.scenarios ?? []).filter((s) => s.area === "customer");
  const [picked, setPicked] = useState<string>("golden_prize_scam");
  const [lang, setLang] = useState<"en" | "bn">("en");
  const check = useAction<PauseResult>();
  const current = scenarios.find((s) => s.id === picked) ?? scenarios[0];
  const r = check.data;

  const runCheck = () => {
    if (!current) return;
    check.run(() => post<PauseResult>("/pause-check", "customer", current.request as PauseRequest));
  };

  return (
    <section id="live" className="scroll-mt-20 border-b border-border">
      <div className="mx-auto max-w-7xl px-4 py-24 md:px-6 md:py-32">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div>
            <p className="label-mono">Live · AI-1 Pause Check</p>
            <h2 className="mt-4 font-serif text-5xl leading-[1] tracking-[-0.01em] md:text-6xl">
              Run a real check.
              <br />
              <span className="italic text-muted-foreground">Nothing is scripted.</span>
            </h2>
            <p className="mt-6 max-w-md text-muted-foreground">
              Pick a moment from Rina&apos;s evening. The button calls the live model API: the probability, the reasons and the
              &ldquo;not sure&rdquo; state come from the model trained in notebook NB01.
            </p>

            <div className="mt-8 space-y-2" role="radiogroup" aria-label="Scenarios">
              {demo.warming && <p className="text-sm text-muted-foreground">Starting the AI engines…</p>}
              {demo.error && <ErrorBox error={demo.error} />}
              {scenarios.map((s) => {
                const on = s.id === current?.id;
                const req = s.request as PauseRequest;
                return (
                  <button
                    key={s.id}
                    role="radio"
                    aria-checked={on}
                    onClick={() => {
                      setPicked(s.id);
                      check.reset();
                    }}
                    className={cn(
                      "w-full rounded-2xl border p-4 text-left transition-colors",
                      on ? "border-foreground bg-card" : "border-border hover:border-foreground/30",
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium">{s.title}</span>
                      <span className="num font-mono text-xs text-muted-foreground">{tk(req.amount)}</span>
                    </div>
                    {on && s.story && <p className="mt-2 text-sm text-muted-foreground">{s.story}</p>}
                  </button>
                );
              })}
            </div>
            <button
              onClick={runCheck}
              disabled={!current || check.running}
              className="mt-6 inline-flex h-12 items-center gap-2 rounded-full bg-foreground px-6 text-sm font-semibold text-background transition-transform hover:-translate-y-0.5 disabled:opacity-50"
            >
              {check.running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              {check.warming ? "Waking the AI engines…" : check.running ? "Checking…" : "Run the Pause Check"}
            </button>
          </div>

          <div className="relative min-h-[520px] rounded-3xl border border-border bg-card p-6 md:p-8" aria-live="polite">
            <AnimatePresence mode="wait">
              {!r && !check.error && (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex h-full min-h-[460px] flex-col items-center justify-center gap-4 text-center"
                >
                  <div className="relative grid size-24 place-items-center">
                    <span className="absolute inset-0 rounded-full border border-border" />
                    <span className={cn("absolute inset-2 rounded-full border border-dashed border-border", check.running && "animate-spin")} />
                    <span className="flex gap-1.5">
                      <span className="h-7 w-2 rounded-sm bg-foreground" />
                      <span className="h-7 w-2 rounded-sm bg-volt" />
                    </span>
                  </div>
                  <p className="max-w-xs text-sm text-muted-foreground">
                    {check.running ? "Scoring the transfer, checking how sure the model is, and writing the reasons…" : "The result appears here."}
                  </p>
                </motion.div>
              )}
              {check.error && <ErrorBox key="err" error={check.error} retry={runCheck} />}
              {r && (
                <motion.div key={r.trace_id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-7">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <RiskBadge state={riskStateOf(r.risk_level, r.uncertainty_state)} className="text-sm" />
                    <div className="flex rounded-full border border-border p-0.5 text-xs" role="group" aria-label="Language">
                      {(["en", "bn"] as const).map((l) => (
                        <button
                          key={l}
                          onClick={() => setLang(l)}
                          aria-pressed={lang === l}
                          className={cn("rounded-full px-3 py-1", lang === l ? "bg-foreground text-background" : "text-muted-foreground")}
                        >
                          {l === "en" ? "English" : "বাংলা"}
                        </button>
                      ))}
                    </div>
                  </div>

                  <ProbabilityMeter
                    p={r.calibrated_probability}
                    label="Calibrated chance this is a scam"
                    marks={[
                      { at: r.thresholds.amber_p, label: "warning" },
                      { at: r.thresholds.red_p, label: "pause" },
                    ]}
                  />

                  {r.uncertainty_state === "unsure" && (
                    <div className="rounded-2xl border border-dashed border-unsure/60 p-4 text-sm">
                      <p className="font-medium">The AI says it is not sure, so a person will check.</p>
                      <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                        {r.reasons_for_unsure.map((u) => (
                          <li key={u}>{unsureText(u)}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-medium">Why</h3>
                      <OutputChip type="model">Model reasons · TreeSHAP</OutputChip>
                    </div>
                    <ReasonList reasons={r.reasons} lang={lang} />
                    <p className={cn("mt-4 text-sm text-muted-foreground", lang === "bn" && "bn")}>
                      {lang === "bn" ? r.counterfactual.text_bn : r.counterfactual.text_en}
                    </p>
                  </div>

                  {r.note_check && (
                    <div className="rounded-2xl bg-muted/60 p-4">
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <h3 className="text-sm font-medium">
                          The message she received: {lang === "bn" ? r.note_check.family_text_bn : r.note_check.family_text_en}
                        </h3>
                        <OutputChip type="model">AI-2 text check</OutputChip>
                      </div>
                      <HighlightedText
                        text={(current?.request as PauseRequest).note ?? ""}
                        highlights={r.note_check.highlights}
                        className="bn text-sm"
                      />
                    </div>
                  )}

                  <div>
                    <h3 className="mb-2 text-sm font-medium">What Rina can do — she is never blocked</h3>
                    <div className="flex flex-wrap gap-2">
                      {r.recommendation.map((a) => (
                        <span key={a} className={cn("rounded-full border border-border px-3 py-1 text-sm", lang === "bn" && "bn")}>
                          {actionText(a, lang)}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
                    <p className="font-mono text-[11px] text-faint">
                      {r.model_version} · trace {r.trace_id} · synthetic data
                    </p>
                    <Link
                      href={`/customer/send?scenario=${current?.id ?? ""}`}
                      className="inline-flex items-center gap-1 text-sm font-medium underline-offset-4 hover:underline"
                    >
                      Open it in the customer app <ArrowUpRight className="size-3.5" />
                    </Link>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
