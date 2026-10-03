"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, ChevronLeft, CircleHelp, Loader2, Phone as PhoneIcon, Timer, TriangleAlert, Users } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { AreaIntro, CustomerShell } from "@/components/customer/phone";
import { ErrorBox } from "@/components/shell/states";
import { OutputChip, RiskBadge, riskStateOf } from "@/components/trust/chips";
import { actionText, HighlightedText, ProbabilityMeter, unsureText } from "@/components/trust/evidence";
import { ReasonTiles, RiskDial } from "@/components/trust/visuals";
import { EmptyInspector, Inspector, InspectorSection, KV, SummaryChips, TraceFooter } from "@/components/trust/inspector";
import { post } from "@/lib/api";
import { num, pct, tk } from "@/lib/format";
import { useLang } from "@/lib/i18n";
import type { Demo, PauseRequest, PauseResult } from "@/lib/types";
import { useAction, usePublic } from "@/lib/use-api";
import { cn } from "@/lib/utils";

type Step = "form" | "checking" | "result" | "wait" | "verify" | "confirm" | "sent";

type Form = {
  recipient_wallet: string;
  amount: string;
  note: string;
  hour: string;
  channel: "app" | "ussd";
  minutes: string;
  device: boolean;
  pin: boolean;
};

const EMPTY: Form = { recipient_wallet: "", amount: "", note: "", hour: "19.5", channel: "app", minutes: "", device: false, pin: false };

function fromScenario(r: PauseRequest): Form {
  return {
    recipient_wallet: r.recipient_wallet,
    amount: String(r.amount),
    note: r.note ?? "",
    hour: String(r.hour ?? 19.5),
    channel: r.channel ?? "app",
    minutes: r.simulated_context?.minutes_since_cash_in != null ? String(r.simulated_context.minutes_since_cash_in) : "",
    device: !!r.simulated_context?.device_changed_recently,
    pin: !!r.simulated_context?.pin_reset_recently,
  };
}

const STAGES = ["Reading 19 behaviour signals", "Scoring with the model", "Checking how sure it is", "Writing the reasons"];

function SendFlow() {
  const params = useSearchParams();
  const demo = usePublic<Demo>("/demo");
  const scenarios = useMemo(() => (demo.data?.scenarios ?? []).filter((s) => s.area === "customer"), [demo.data]);
  const { t, lang } = useLang();
  const [form, setForm] = useState<Form>(EMPTY);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [step, setStep] = useState<Step>("form");
  const [stage, setStage] = useState(0);
  const [latency, setLatency] = useState<number | null>(null);
  const [left, setLeft] = useState(600);
  const check = useAction<PauseResult>();
  const r = check.data;

  // Prefill from ?scenario= once the scenario list arrives (adjusting state during render, not in an effect).
  const wanted = params.get("scenario") ?? "golden_prize_scam";
  if (scenarios.length && loadedFor !== wanted) {
    const s = scenarios.find((x) => x.id === wanted) ?? scenarios[0];
    setLoadedFor(wanted);
    setForm(fromScenario(s.request as PauseRequest));
  }

  useEffect(() => {
    if (step !== "checking") return;
    const id = setInterval(() => setStage((s) => Math.min(STAGES.length - 1, s + 1)), 380);
    return () => clearInterval(id);
  }, [step]);

  useEffect(() => {
    if (step !== "wait") return;
    const id = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [step]);

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = Number(form.amount);
    if (!/^C\d{6}$/.test(form.recipient_wallet)) return toast.error("Receiver wallet looks like C followed by 6 digits, e.g. C008170.");
    if (!(amount > 0 && amount <= 1_000_000)) return toast.error("Enter an amount between Tk 1 and Tk 1,000,000.");
    const ctx: PauseRequest["simulated_context"] = {};
    if (form.minutes !== "") ctx.minutes_since_cash_in = Number(form.minutes);
    if (form.device) ctx.device_changed_recently = true;
    if (form.pin) ctx.pin_reset_recently = true;
    const body: PauseRequest = {
      sender_id: "C000021",
      recipient_wallet: form.recipient_wallet,
      amount,
      hour: Number(form.hour),
      channel: form.channel,
      ...(form.note.trim() ? { note: form.note.trim() } : {}),
      ...(Object.keys(ctx).length ? { simulated_context: ctx } : {}),
    };
    setStage(0);
    setStep("checking");
    const t0 = performance.now();
    const [out] = await Promise.all([check.run(() => post<PauseResult>("/pause-check", "customer", body)), new Promise((res) => setTimeout(res, 1500))]);
    setLatency(Math.round(performance.now() - t0));
    setStep(out ? "result" : "form");
  };

  const restart = () => {
    setStep("form");
    setLeft(600);
    check.reset();
  };

  const level = r ? riskStateOf(r.risk_level, r.uncertainty_state) : null;
  const paused = r && r.uncertainty_state !== "unsure" && r.risk_level === "high";
  const lowRisk = r && r.uncertainty_state !== "unsure" && r.risk_level === "low";

  const phone = (
    <AnimatePresence mode="wait">
      {step === "form" && (
        <motion.form key="form" onSubmit={submit} className="space-y-4 pt-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <p className="text-xl font-semibold tracking-tight">{t("send_money")}</p>
          {scenarios.length > 0 && (
            <div className="no-scrollbar flex gap-1.5 overflow-x-auto pb-1" aria-label="Demo scenarios">
              {scenarios.map((s) => (
                <Link
                  key={s.id}
                  href={`/customer/send?scenario=${s.id}`}
                  scroll={false}
                  className={cn(
                    "shrink-0 rounded-full border px-3 py-1 text-xs",
                    loadedFor === s.id ? "border-foreground bg-foreground text-background" : "border-border text-muted-foreground",
                  )}
                >
                  {s.title.split(":")[0].split("(")[0].trim()}
                </Link>
              ))}
            </div>
          )}
          <label className="block space-y-1.5">
            <span className="text-sm text-muted-foreground">{t("receiver")}</span>
            <input
              value={form.recipient_wallet}
              onChange={(e) => set("recipient_wallet", e.target.value.toUpperCase())}
              placeholder="C008170"
              className="h-11 w-full rounded-xl border border-border bg-background px-3 font-mono"
              autoComplete="off"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm text-muted-foreground">{t("amount")}</span>
            <input
              value={form.amount}
              onChange={(e) => set("amount", e.target.value.replace(/[^\d.]/g, ""))}
              inputMode="decimal"
              placeholder="3000"
              className="h-14 w-full rounded-xl border border-border bg-background px-3 font-mono text-2xl"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm text-muted-foreground">{t("note")}</span>
            <textarea
              value={form.note}
              onChange={(e) => set("note", e.target.value)}
              rows={3}
              maxLength={1000}
              className="bn w-full rounded-xl border border-border bg-background p-3 text-sm"
            />
          </label>
          <details className="rounded-xl border border-dashed border-border p-3 text-sm">
            <summary className="cursor-pointer text-muted-foreground">Demo context (simulated)</summary>
            <div className="mt-3 grid gap-3">
              <label className="flex items-center justify-between gap-3">
                <span>Time of day</span>
                <input type="range" min={0} max={23.5} step={0.5} value={form.hour} onChange={(e) => set("hour", e.target.value)} className="w-32" />
                <span className="num w-12 text-right font-mono">{String(Math.floor(Number(form.hour))).padStart(2, "0")}:{Number(form.hour) % 1 ? "30" : "00"}</span>
              </label>
              <label className="flex items-center justify-between gap-3">
                <span>Minutes since a cash-in</span>
                <input
                  value={form.minutes}
                  onChange={(e) => set("minutes", e.target.value.replace(/\D/g, ""))}
                  placeholder="none"
                  className="h-8 w-20 rounded-lg border border-border bg-background px-2 text-right font-mono"
                />
              </label>
              <label className="flex items-center justify-between">
                <span>New phone in the last 3 days</span>
                <input type="checkbox" checked={form.device} onChange={(e) => set("device", e.target.checked)} className="size-4 accent-[var(--volt)]" />
              </label>
              <label className="flex items-center justify-between">
                <span>PIN reset in the last 3 days</span>
                <input type="checkbox" checked={form.pin} onChange={(e) => set("pin", e.target.checked)} className="size-4 accent-[var(--volt)]" />
              </label>
              <label className="flex items-center justify-between">
                <span>Channel</span>
                <select value={form.channel} onChange={(e) => set("channel", e.target.value as "app" | "ussd")} className="h-8 rounded-lg border border-border bg-background px-2">
                  <option value="app">App</option>
                  <option value="ussd">USSD</option>
                </select>
              </label>
            </div>
          </details>
          {check.error && <ErrorBox error={check.error} />}
          <button type="submit" className="h-12 w-full rounded-full bg-foreground font-medium text-background">
            {t("continue")}
          </button>
          <p className="text-center text-xs text-faint">{t("demo_no_money")}</p>
        </motion.form>
      )}

      {step === "checking" && (
        <motion.div key="checking" className="flex min-h-[560px] flex-col items-center justify-center gap-8 text-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="relative grid size-28 place-items-center">
            <motion.span
              className="absolute inset-0 rounded-full border-2 border-dashed border-foreground/30"
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 6, ease: "linear" }}
            />
            <span className="flex gap-2">
              <span className="h-10 w-3 rounded-sm bg-foreground" />
              <span className="h-10 w-3 rounded-sm bg-volt" />
            </span>
          </div>
          <p className="text-lg font-medium">{t("checking")}</p>
          <ul className="space-y-1.5 text-left text-sm">
            {STAGES.map((s, i) => (
              <li key={s} className={cn("flex items-center gap-2 transition-opacity", i <= stage ? "opacity-100" : "opacity-30")}>
                {i < stage ? <CheckCircle2 className="size-4 text-safe" /> : <Loader2 className={cn("size-4", i === stage && "animate-spin")} />}
                {s}
              </li>
            ))}
          </ul>
          {check.warming && <p className="text-xs text-muted-foreground">The free server is waking up (about a minute)…</p>}
        </motion.div>
      )}

      {step === "result" && r && (
        <motion.div key="result" className="space-y-5 pt-2" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
          <button onClick={restart} className="flex items-center gap-1 text-sm text-muted-foreground">
            <ChevronLeft className="size-4" /> {t("back")}
          </button>

          <div className="text-center">
            <RiskDial
              p={r.calibrated_probability}
              size={200}
              className="mx-auto"
              tone={r.uncertainty_state === "unsure" ? "unsure" : undefined}
              label={r.uncertainty_state === "unsure" ? "the AI is not sure" : lang === "bn" ? "প্রতারণার সম্ভাবনা" : "chance this is a scam"}
            />
            <div className="mt-4 flex items-center justify-center gap-2">
              {paused && <span className="flex gap-1"><span className="h-5 w-1.5 rounded-sm bg-foreground" /><span className="h-5 w-1.5 rounded-sm bg-volt" /></span>}
              {lowRisk && <CheckCircle2 className="size-5 text-safe" />}
              {r.uncertainty_state === "unsure" && <CircleHelp className="size-5 text-unsure" />}
              {r.uncertainty_state !== "unsure" && r.risk_level === "medium" && <TriangleAlert className="size-5 text-caution" />}
              <p className="text-xl font-semibold">
                {paused ? t("paused") : lowRisk ? t("looks_fine") : r.uncertainty_state === "unsure" ? t("not_sure") : t("some_signs")}
              </p>
            </div>
            <p className="num mt-1 text-sm text-muted-foreground">
              {tk(r.inputs.amount)} → {form.recipient_wallet}
            </p>
          </div>

          {lowRisk && r.reasons.length > 0 && <p className="-mb-2 text-center text-xs text-muted-foreground">What looked normal</p>}
          {r.reasons.length > 0 && <ReasonTiles reasons={r.reasons} lang={lang} />}
          {!lowRisk && r.note_check && r.note_check.state === "likely_scam" && (
            <p className="flex items-center gap-2 rounded-2xl bg-risk/10 px-3 py-2 text-sm">
              <TriangleAlert className="size-4 shrink-0 text-risk" />
              {lang === "bn" ? r.note_check.family_text_bn : r.note_check.family_text_en}
            </p>
          )}
          {r.uncertainty_state === "unsure" && (
            <p className="rounded-2xl border border-dashed border-unsure/60 px-3 py-2 text-center text-sm text-muted-foreground">
              {r.reasons_for_unsure.map(unsureText).join(" ")}
            </p>
          )}

          {r.human_review === "required" && (
            <p className="rounded-2xl border border-border p-3 text-sm">A team member will look at this large transfer before it is completed. You can still cancel.</p>
          )}

          <div className="space-y-2">
            {lowRisk ? (
              <button onClick={() => setStep("sent")} className="h-12 w-full rounded-full bg-foreground font-medium text-background">
                {t("send_now")}
              </button>
            ) : (
              <>
                {r.recommendation.includes("wait_10_min") && (
                  <button onClick={() => setStep("wait")} className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-foreground font-medium text-background">
                    <Timer className="size-4" /> {t("wait")}
                  </button>
                )}
                <button onClick={() => setStep("verify")} className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border font-medium">
                  <PhoneIcon className="size-4" /> {t("verify")}
                </button>
                {r.recommendation.includes("ask_trusted_contact") && (
                  <button
                    onClick={async () => {
                      const text = `I got a request to send ${tk(r.inputs.amount)} to ${form.recipient_wallet}. My wallet paused it as a possible scam. Can you check with me?`;
                      try {
                        if (navigator.share) await navigator.share({ text });
                        else {
                          await navigator.clipboard.writeText(text);
                          toast.success("Message copied — paste it to someone you trust.");
                        }
                      } catch {
                        /* the person closed the share sheet */
                      }
                    }}
                    className="flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border font-medium"
                  >
                    <Users className="size-4" /> {t("ask")}
                  </button>
                )}
                <button onClick={() => setStep("confirm")} className="w-full py-2 text-sm text-muted-foreground underline underline-offset-4">
                  {t("send_anyway")}
                </button>
                <p className="text-center text-xs text-faint">{t("never_blocked")}</p>
              </>
            )}
          </div>
        </motion.div>
      )}

      {step === "wait" && (
        <motion.div key="wait" className="flex min-h-[560px] flex-col items-center justify-center gap-6 text-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <p className="num font-mono text-6xl font-semibold tracking-tight">
            {String(Math.floor(left / 60)).padStart(2, "0")}:{String(left % 60).padStart(2, "0")}
          </p>
          <p className="text-lg">{t("waiting")}</p>
          <p className="max-w-xs text-sm text-muted-foreground">Scammers push you to act fast. Real prizes never ask for a fee. The transfer is kept as a draft until you decide.</p>
          <button onClick={() => setStep("result")} className="text-sm underline underline-offset-4">
            {t("back")}
          </button>
        </motion.div>
      )}

      {step === "verify" && r && (
        <motion.div key="verify" className="space-y-5 pt-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <button onClick={() => setStep("result")} className="flex items-center gap-1 text-sm text-muted-foreground">
            <ChevronLeft className="size-4" /> {t("back")}
          </button>
          <p className="text-xl font-semibold">{t("verify")}</p>
          <p className="text-sm">{t("call_official")}</p>
          <KV
            rows={[
              ["Receiver wallet age", `${num(r.key_facts.recipient_age_days)} days`],
              ["People who sent to it this week", num(r.key_facts.receiver_senders_7d)],
              ["You sent to it before", r.key_facts.first_time_pair ? "No, first time" : "Yes"],
            ]}
          />
          <button onClick={restart} className="h-12 w-full rounded-full bg-foreground font-medium text-background">
            Cancel this transfer
          </button>
        </motion.div>
      )}

      {step === "confirm" && r && (
        <motion.div key="confirm" className="flex min-h-[560px] flex-col justify-center gap-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <p className="text-xl font-semibold">Are you sure?</p>
          <p className="text-sm text-muted-foreground">
            You can still send. If this turns out to be a scam, report it quickly: the sooner it is reported, the more likely the money can be traced.
          </p>
          <button onClick={() => setStep("sent")} className="h-12 w-full rounded-full border border-border font-medium">
            Yes, send {tk(r.inputs.amount)}
          </button>
          <button onClick={() => setStep("result")} className="h-12 w-full rounded-full bg-foreground font-medium text-background">
            No, go back
          </button>
        </motion.div>
      )}

      {step === "sent" && (
        <motion.div key="sent" className="flex min-h-[560px] flex-col items-center justify-center gap-4 text-center" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
          <CheckCircle2 className="size-16 text-safe" strokeWidth={1.5} />
          <p className="text-xl font-semibold">{t("sent")}</p>
          <p className="text-sm text-muted-foreground">{t("demo_no_money")}</p>
          <button onClick={restart} className="mt-4 text-sm underline underline-offset-4">
            {t("start_again")}
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );

  const inspector = (
    <Inspector
      summary={
        r ? (
          <SummaryChips
            items={[
              ["probability", pct(r.calibrated_probability)],
              ["state", r.state.replace(/_/g, " ")],
              ["conformal", `{ ${r.conformal_set.join(", ")} }`],
              ["unusual input", r.ood_flag ? "yes" : "no"],
              ["latency", latency != null ? `${latency} ms` : "—"],
            ]}
          />
        ) : (
          <p className="text-sm text-muted-foreground">Raw score, calibrated probability, conformal set, TreeSHAP weights, rules and the brief appear here after a check.</p>
        )
      }
    >
      {!r ? (
        <EmptyInspector text="Press Continue. This panel then shows exactly what the models returned: the raw score, the calibrated probability, the conformal set, the unusual-input flag, every reason with its weight, the business rules that fired and the generated brief." />
      ) : (
        <>
          <InspectorSection title="Decision" chip={level && <RiskBadge state={level} />}>
            <KV
              rows={[
                ["Decision state", r.state.replace(/_/g, " ")],
                ["Risk level (frozen thresholds)", r.risk_level],
                ["Certainty", r.uncertainty_state],
                ["Human review", r.human_review.replace(/_/g, " ")],
                ["Offered actions", r.recommendation.map((a) => actionText(a)).join(" · ")],
              ]}
            />
          </InspectorSection>
          <InspectorSection title="AI-1 model output" chip={<OutputChip type="model" />}>
            <ProbabilityMeter
              p={r.calibrated_probability}
              label="Calibrated scam probability"
              marks={[
                { at: r.thresholds.amber_p, label: "warning" },
                { at: r.thresholds.red_p, label: "pause" },
              ]}
            />
            <KV
              rows={[
                ["Raw model score", r.model_score.toFixed(4)],
                ["Conformal set (90%)", `{ ${r.conformal_set.join(", ")} }`],
                ["Unusual input (novelty)", r.ood_flag ? "yes" : "no"],
                ["Response time", latency != null ? `${latency} ms` : "—"],
              ]}
            />
          </InspectorSection>
          <InspectorSection title="Reasons · exact TreeSHAP" chip={<OutputChip type="model" />}>
            <div className="overflow-hidden rounded-2xl border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-normal">Signal</th>
                    <th className="px-3 py-2 text-right font-normal">Value</th>
                    <th className="px-3 py-2 text-right font-normal">Push</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {r.reasons.map((x) => (
                    <tr key={x.feature}>
                      <td className="px-3 py-2 font-mono text-xs">{x.feature}</td>
                      <td className="num px-3 py-2 text-right font-mono text-xs">{num(x.value, 2)}</td>
                      <td className="num px-3 py-2 text-right font-mono text-xs">{x.contribution >= 0 ? "+" : ""}{x.contribution.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm text-muted-foreground">
              {r.counterfactual?.text_en ?? (lowRisk ? "Low risk: these are the signals that pulled the score down (negative push)." : "")}
            </p>
          </InspectorSection>
          {r.rule_hits.length > 0 && (
            <InspectorSection title="Business rules" chip={<OutputChip type="rule" />}>
              <ul className="space-y-1 text-sm">
                {r.rule_hits.map((h) => (
                  <li key={h.id}>
                    <span className="font-mono text-xs text-faint">{h.id}</span> {h.text}
                  </li>
                ))}
              </ul>
            </InspectorSection>
          )}
          {r.note_check && (
            <InspectorSection title="AI-2 message check" chip={<OutputChip type="model" />}>
              <HighlightedText text={form.note} highlights={r.note_check.highlights} className="bn rounded-2xl bg-muted/50 p-3 text-sm" />
              <KV
                rows={[
                  ["Scam probability", pct(r.note_check.p_scam)],
                  ...r.note_check.top_families.map((f) => [f.family.replace(/_/g, " "), pct(f.probability)] as [string, string]),
                  ["Contains instructions aimed at AI", r.note_check.contains_ai_instructions ? "yes" : "no"],
                ]}
              />
            </InspectorSection>
          )}
          <InspectorSection title="AI-7 brief" chip={<OutputChip type="generated">{`Generated · ${r.brief.source}`}</OutputChip>}>
            <p className="bn text-sm">{r.brief.bangla}</p>
            <p className="text-sm text-muted-foreground">{r.brief.english}</p>
            <p className="font-mono text-[11px] text-faint">
              cards {r.brief.card_ids.join(", ")} · evidence {r.evidence_ids.join(", ")}
            </p>
          </InspectorSection>
          <TraceFooter trace={r.trace_id} model={r.model_version} data={r.data_version} />
        </>
      )}
    </Inspector>
  );

  return (
    <CustomerShell
      intro={
        <AreaIntro
          label="Customer · Send money · AI-1 + AI-2 + AI-7"
          title={
            <>
              Pause <span className="italic">before</span> the money moves.
            </>
          }
          text="Every transfer is checked in under a second. High risk pauses with reasons; “not sure” asks a person; low risk sends straight away."
        />
      }
      phone={phone}
      inspector={inspector}
    />
  );
}

export default function SendPage() {
  return (
    <Suspense>
      <SendFlow />
    </Suspense>
  );
}
