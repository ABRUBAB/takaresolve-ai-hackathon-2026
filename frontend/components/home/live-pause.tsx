"use client";

import Link from "next/link";
import { ArrowUpRight, ChevronDown, CircleHelp, Loader2, MessageSquareWarning, ShieldCheck, ShieldX } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { ErrorBox } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { actionText, HighlightedText, ProbabilityMeter, ReasonList, unsureText } from "@/components/trust/evidence";
import { ReasonTiles, RiskDial } from "@/components/trust/visuals";
import ClickSpark from "@/components/reactbits/ClickSpark";
import { BorderBeam } from "@/components/ui/border-beam";
import { post } from "@/lib/api";
import { tk } from "@/lib/format";
import type { Demo, PauseRequest, PauseResult } from "@/lib/types";
import { useAction, usePublic } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import { TapHint } from "@/components/ui/tap-hint";

const SHORT: Record<string, string> = {
  golden_prize_scam: "Prize scam",
  normal_user: "Family transfer",
  new_device_takeover: "New phone at night",
};

export function LivePause() {
  const demo = usePublic<Demo>("/demo");
  const scenarios = (demo.data?.scenarios ?? []).filter((s) => s.area === "customer");
  const [picked, setPicked] = useState<string>("golden_prize_scam");
  const [lang, setLang] = useState<"en" | "bn">("en");
  const [details, setDetails] = useState(false);
  const check = useAction<PauseResult>();
  const current = scenarios.find((s) => s.id === picked) ?? scenarios[0];
  const req = current?.request as PauseRequest | undefined;
  const r = check.data;

  const run = () => {
    if (!req) return;
    check.run(() => post<PauseResult>("/pause-check", "customer", req));
  };

  const unsure = r?.uncertainty_state === "unsure";
  const high = r && !unsure && r.risk_level === "high";
  const low = r && !unsure && r.risk_level === "low";

  return (
    <section id="live" className="scroll-mt-16 border-b border-border">
      <div className="mx-auto max-w-[1760px] px-4 py-24 md:px-8 xl:px-12 md:py-32">
        <div className="max-w-2xl">
          <p className="label-mono">Live · real model, real API</p>
          <h2 className="mt-4 font-serif text-5xl leading-[1] md:text-6xl">
            Send it. <span className="italic text-muted-foreground">Watch it pause.</span>
          </h2>
        </div>

        <div className="mt-14 grid items-start gap-10 lg:grid-cols-[260px_380px_minmax(0,1fr)]">
          {/* scenarios */}
          <div className="space-y-2" role="radiogroup" aria-label="Scenarios">
            {demo.warming && <p className="text-sm text-muted-foreground">Waking the AI engines…</p>}
            {demo.error && <ErrorBox error={demo.error} />}
            {scenarios.map((s, i) => {
              const on = s.id === current?.id;
              return (
                <button
                  key={s.id}
                  role="radio"
                  aria-checked={on}
                  onClick={() => {
                    setPicked(s.id);
                    check.reset();
                    setDetails(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition-all",
                    on ? "border-foreground bg-card" : "border-border opacity-70 hover:opacity-100",
                  )}
                >
                  <span className={cn("grid size-9 shrink-0 place-items-center rounded-full font-mono text-xs", on ? "bg-foreground text-background" : "bg-muted")}>
                    0{i + 1}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{SHORT[s.id] ?? s.title}</span>
                    <span className="num block font-mono text-xs text-muted-foreground">{tk((s.request as PauseRequest).amount)}</span>
                  </span>
                </button>
              );
            })}
          </div>

          {/* the phone */}
          <div className="relative mx-auto w-full max-w-[380px] rounded-[2.6rem] border border-border bg-background p-3 shadow-2xl shadow-black/40">
            {check.running && <BorderBeam size={120} duration={3} colorFrom="#d7ff3a" colorTo="#ffffff" />}
            <ClickSpark sparkColor="#d7ff3a" sparkCount={10} sparkRadius={22}>
            <div className="relative min-h-[600px] overflow-hidden rounded-[2.1rem] border border-border bg-card px-5 pb-6 pt-5">
              <div className="mb-4 flex items-center justify-between font-mono text-[11px] text-muted-foreground" aria-hidden="true">
                <span>19:30</span>
                <span className="h-5 w-20 rounded-full bg-background" />
                <span>4G</span>
              </div>
              <AnimatePresence mode="wait">
                {!r && (
                  <motion.div key={`draft-${picked}`} className="flex min-h-[520px] flex-col" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                    <p className="text-sm text-muted-foreground">Send money</p>
                    <p className="num mt-2 font-mono text-5xl font-semibold tracking-tight">{req ? tk(req.amount) : "—"}</p>
                    <p className="mt-1 font-mono text-sm text-muted-foreground">to {req?.recipient_wallet ?? "—"}</p>
                    {req?.note && (
                      <div className="mt-6 rounded-2xl rounded-tl-sm bg-muted p-3">
                        <p className="mb-1 flex items-center gap-1 text-[11px] text-muted-foreground">
                          <MessageSquareWarning className="size-3" /> Message Rubab received
                        </p>
                        <p className="bn line-clamp-4 text-sm">{req.note}</p>
                      </div>
                    )}
                    {req?.simulated_context && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {req.simulated_context.minutes_since_cash_in != null && <Chip>cash-in {req.simulated_context.minutes_since_cash_in} min ago</Chip>}
                        {req.simulated_context.device_changed_recently && <Chip>new phone</Chip>}
                        {req.simulated_context.pin_reset_recently && <Chip>PIN reset</Chip>}
                      </div>
                    )}
                    <div className="mt-auto pt-8">
                      {check.error && <ErrorBox error={check.error} retry={run} />}
                      {!check.running && <TapHint className="mb-3 w-full justify-center">Press Send to run the real check</TapHint>}
                      <button
                        onClick={run}
                        disabled={!req || check.running}
                        className="flex h-13 w-full items-center justify-center gap-2 rounded-full bg-foreground font-medium text-background transition-transform hover:scale-[1.02] disabled:opacity-60"
                      >
                        {check.running && <Loader2 className="size-4 animate-spin" />}
                        {check.warming ? "Waking the AI engines…" : check.running ? "Checking before you send…" : "Send"}
                      </button>
                      <p className="mt-2 text-center text-[11px] text-faint">Synthetic demo · no real money moves</p>
                    </div>
                  </motion.div>
                )}
                {r && (
                  <motion.div key={r.trace_id} className="flex min-h-[520px] flex-col items-center text-center" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                    <RiskDial p={r.calibrated_probability} size={190} tone={unsure ? "unsure" : undefined} label={unsure ? "the AI is not sure" : "chance this is a scam"} />
                    <div className="mt-4 flex items-center gap-2">
                      {high && <ShieldX className="size-5 text-risk" />}
                      {low && <ShieldCheck className="size-5 text-safe" />}
                      {unsure && <CircleHelp className="size-5 text-unsure" />}
                      <p className={cn("text-xl font-semibold", lang === "bn" && "bn")}>
                        {high
                          ? lang === "bn"
                            ? "আপনার নিরাপত্তার জন্য থামানো হয়েছে"
                            : "Paused for your safety"
                          : low
                            ? lang === "bn"
                              ? "ঠিক আছে বলে মনে হচ্ছে"
                              : "Looks fine"
                            : unsure
                              ? lang === "bn"
                                ? "নিশ্চিত নয় — একজন কর্মী যাচাই করবেন"
                                : "Not sure — a person will check"
                              : "Some warning signs"}
                      </p>
                    </div>
                    {low && r.reasons.length > 0 && <p className="mt-5 text-xs text-muted-foreground">{lang === "bn" ? "যা স্বাভাবিক দেখাল" : "What looked normal"}</p>}
                    {r.reasons.length > 0 && <ReasonTiles reasons={r.reasons} lang={lang} className={cn("w-full text-left", low ? "mt-2" : "mt-5")} />}
                    <div className="mt-auto w-full space-y-2 pt-6">
                      {low ? (
                        <Link href={`/customer/send?scenario=${current?.id ?? ""}`} className="flex h-12 items-center justify-center rounded-full bg-foreground text-sm font-medium text-background hover:opacity-90">
                          Send now
                        </Link>
                      ) : (
                        r.recommendation
                          .filter((a) => a !== "continue_anyway")
                          .slice(0, 2)
                          .map((a, i) => (
                            <Link
                              key={a}
                              href={`/customer/send?scenario=${current?.id ?? ""}`}
                              className={cn("flex h-11 items-center justify-center rounded-full text-sm transition-opacity hover:opacity-85", i === 0 ? "bg-foreground font-medium text-background" : "border border-border")}
                            >
                              {actionText(a, lang)}
                            </Link>
                          ))
                      )}
                      {!low && (
                        <Link href={`/customer/send?scenario=${current?.id ?? ""}`} className="block text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground">
                          {lang === "bn" ? "আমি নিশ্চিত, পাঠাব" : "I'm sure, send anyway"}
                        </Link>
                      )}
                      <p className="pt-1 text-[11px] text-faint">These open the full flow in {"Rubab"}&apos;s app</p>
                      <button onClick={() => check.reset()} className="pt-1 text-xs text-faint hover:text-foreground">
                        Try again
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            </ClickSpark>
          </div>

          {/* the analysis, behind a click */}
          <div className="min-w-0">
            {!r ? (
              <div className="space-y-4 text-muted-foreground">
                <p className="max-w-sm">Press <span className="text-foreground">Send</span> on the phone. The answer comes from the model trained in notebook NB01, through the live API.</p>
                <ul className="space-y-2 text-sm">
                  <li className="flex gap-2"><span className="mt-2 size-1.5 rounded-full bg-risk" /> High risk pauses, with reasons</li>
                  <li className="flex gap-2"><span className="mt-2 size-1.5 rounded-full bg-unsure" /> “Not sure” asks a person</li>
                  <li className="flex gap-2"><span className="mt-2 size-1.5 rounded-full bg-safe" /> Low risk sends straight away</li>
                </ul>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => setDetails((d) => !d)}
                    aria-expanded={details}
                    className="inline-flex h-11 items-center gap-2 rounded-full border border-border px-5 text-sm hover:border-foreground/40"
                  >
                    {details ? "Hide the model analysis" : "Show the model analysis"}
                    <ChevronDown className={cn("size-4 transition-transform", details && "rotate-180")} />
                  </button>
                  <div className="flex rounded-full border border-border p-0.5 text-xs" role="group" aria-label="Language">
                    {(["en", "bn"] as const).map((l) => (
                      <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l} className={cn("rounded-full px-3 py-1.5", lang === l ? "bg-foreground text-background" : "text-muted-foreground")}>
                        {l === "en" ? "English" : "বাংলা"}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-4 rounded-3xl border border-border bg-card p-6">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">
                      {low ? (lang === "bn" ? "কেন এটি ঠিক আছে বলে মনে হচ্ছে" : "Why it looks fine") : lang === "bn" ? "কেন এটি দেখছি?" : "Why Rubab sees this"}
                    </p>
                    <OutputChip type="model">Model reasons</OutputChip>
                  </div>
                  <ReasonList reasons={r.reasons} lang={lang} />
                  {r.counterfactual && (
                    <p className={cn("text-sm text-muted-foreground", lang === "bn" && "bn")}>{lang === "bn" ? r.counterfactual.text_bn : r.counterfactual.text_en}</p>
                  )}
                  {r.note_check && (
                    <p className={cn("rounded-2xl bg-muted/60 px-3 py-2 text-sm", lang === "bn" && "bn")}>
                      {lang === "bn" ? "বার্তাটি: " : "The message: "}
                      {lang === "bn" ? r.note_check.family_text_bn : r.note_check.family_text_en}
                    </p>
                  )}
                </div>
                <AnimatePresence initial={false}>
                  {details && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="space-y-6 rounded-3xl border border-border bg-card p-6">
                        <ProbabilityMeter
                          p={r.calibrated_probability}
                          label="Calibrated probability vs the frozen thresholds"
                          marks={[
                            { at: r.thresholds.amber_p, label: "warning" },
                            { at: r.thresholds.red_p, label: "pause" },
                          ]}
                        />
                        {unsure && (
                          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                            {r.reasons_for_unsure.map((u) => (
                              <li key={u}>{unsureText(u)}</li>
                            ))}
                          </ul>
                        )}
                        <div>
                          <div className="mb-2 flex items-center justify-between">
                            <p className="text-sm font-medium">Exact TreeSHAP weights</p>
                            <OutputChip type="model" />
                          </div>
                          <div className="divide-y divide-border rounded-2xl border border-border text-sm">
                            {r.reasons.map((x) => (
                              <div key={x.feature} className="flex justify-between gap-3 px-3 py-2 font-mono text-xs">
                                <span>{x.feature}</span>
                                <span>
                                  value {x.value.toFixed(2)} · push {x.contribution >= 0 ? "+" : ""}
                                  {x.contribution.toFixed(2)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                        {r.note_check && req?.note && (
                          <div>
                            <div className="mb-2 flex items-center justify-between">
                              <p className="text-sm font-medium">{lang === "bn" ? r.note_check.family_text_bn : r.note_check.family_text_en}</p>
                              <OutputChip type="model">AI-2</OutputChip>
                            </div>
                            <HighlightedText text={req.note} highlights={r.note_check.highlights} className="bn rounded-2xl bg-muted/60 p-3 text-sm" />
                          </div>
                        )}
                        <div>
                          <div className="mb-2 flex items-center justify-between">
                            <p className="text-sm font-medium">Brief</p>
                            <OutputChip type="generated">{`Generated · ${r.brief.source}`}</OutputChip>
                          </div>
                          <p className={cn("text-sm text-muted-foreground", lang === "bn" && "bn")}>{lang === "bn" ? r.brief.bangla : r.brief.english}</p>
                        </div>
                        <p className="font-mono text-[11px] text-faint">
                          {r.model_version} · trace {r.trace_id}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
                <Link href={`/customer/send?scenario=${current?.id ?? ""}`} className="inline-flex items-center gap-1 text-sm font-medium underline-offset-4 hover:underline">
                  Open it in Rubab&apos;s app <ArrowUpRight className="size-3.5" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full border border-dashed border-border px-2 py-0.5 text-[11px] text-muted-foreground">{children}</span>;
}
