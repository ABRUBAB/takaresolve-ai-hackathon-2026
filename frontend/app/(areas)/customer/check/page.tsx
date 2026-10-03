"use client";

import { Bot, CircleHelp, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { AreaIntro, CustomerShell } from "@/components/customer/phone";
import { ErrorBox } from "@/components/shell/states";
import { OutputChip } from "@/components/trust/chips";
import { HighlightedText, ProbabilityMeter } from "@/components/trust/evidence";
import { EmptyInspector, Inspector, InspectorSection, KV, SummaryChips, TraceFooter } from "@/components/trust/inspector";
import { RiskDial } from "@/components/trust/visuals";
import { post } from "@/lib/api";
import { pct } from "@/lib/format";
import { useLang } from "@/lib/i18n";
import type { Demo, Envelope, TextCheck } from "@/lib/types";
import { useAction, usePublic } from "@/lib/use-api";
import { cn } from "@/lib/utils";

type Result = Envelope & TextCheck;

export default function CheckPage() {
  const demo = usePublic<Demo>("/demo");
  const examples = (demo.data?.scenarios ?? []).filter((s) => s.area === "customer_text");
  const [text, setText] = useState("");
  const [checked, setChecked] = useState("");
  const { t, lang } = useLang();
  const check = useAction<Result>();
  const r = check.data;

  const run = (value = text) => {
    if (value.trim().length < 3) return;
    setChecked(value.trim());
    check.run(() => post<Result>("/text-check", "customer", { text: value.trim() }));
  };

  const verdict = r?.state === "likely_scam" ? "scam" : r?.state === "likely_safe" ? "safe" : r ? "unsure" : null;

  return (
    <CustomerShell
      intro={
        <AreaIntro
          label="Customer · Check a message · AI-2"
          title={
            <>
              Is this SMS a <span className="italic">scam</span>?
            </>
          }
          text="Paste a message in Bangla, Banglish or English. The model names the scam type and highlights the phrases that drove the verdict. If it is not sure, it says so."
        />
      }
      phone={
        <div className="space-y-4 pt-2">
          <p className="text-xl font-semibold tracking-tight">{t("check_sms")}</p>
          <div className="flex flex-wrap gap-1.5">
            {examples.map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  const v = String((s.request as { text: string }).text);
                  setText(v);
                  run(v);
                }}
                className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {s.title}
              </button>
            ))}
          </div>
          <label className="block space-y-1.5">
            <span className="text-sm text-muted-foreground">{t("paste_here")}</span>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={5}
              maxLength={1000}
              className="bn w-full rounded-xl border border-border bg-background p-3 text-sm"
            />
          </label>
          <button
            onClick={() => run()}
            disabled={check.running || text.trim().length < 3}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-foreground font-medium text-background disabled:opacity-50"
          >
            {check.running && <Loader2 className="size-4 animate-spin" />}
            {t("check_message")}
          </button>
          {check.error && <ErrorBox error={check.error} />}
          <AnimatePresence mode="wait">
            {r && (
              <motion.div
                key={r.trace_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "space-y-3 rounded-3xl p-4",
                  verdict === "scam" && "bg-risk/10",
                  verdict === "safe" && "bg-safe/10",
                  verdict === "unsure" && "border-2 border-dashed border-unsure/60",
                )}
              >
                <RiskDial p={r.p_scam} size={150} className="mx-auto" tone={verdict === "unsure" ? "unsure" : undefined} label="scam probability" />
                <div className="flex items-center justify-center gap-2">
                  {verdict === "scam" && <ShieldAlert className="size-6 text-risk" />}
                  {verdict === "safe" && <ShieldCheck className="size-6 text-safe" />}
                  {verdict === "unsure" && <CircleHelp className="size-6 text-unsure" />}
                  <p className="text-lg font-semibold">
                    {verdict === "scam" ? t("likely_scam") : verdict === "safe" ? t("likely_safe") : t("unsure_text")}
                  </p>
                </div>
                {verdict !== "safe" && r.family !== "legit" && (
                  <p className="text-sm">{lang === "bn" ? r.family_text_bn : r.family_text_en}</p>
                )}
                {r.contains_ai_instructions && (
                  <p className="flex gap-2 rounded-xl bg-background/60 p-3 text-sm">
                    <Bot className="mt-0.5 size-4 shrink-0" />
                    This message contains instructions aimed at an AI (“ignore previous instructions…”). That is a common trick: treat it with extra care.
                  </p>
                )}
                <HighlightedText text={checked} highlights={r.highlights} className="bn text-sm leading-relaxed" />
                <p className="text-xs text-muted-foreground">{r.note}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      }
      inspector={
        <Inspector
          summary={
            r ? (
              <SummaryChips items={[["scam probability", pct(r.p_scam)], ["family", r.family.replace(/_/g, " ")], ["AI instructions", r.contains_ai_instructions ? "detected" : "none"]]} />
            ) : (
              <p className="text-sm text-muted-foreground">Scam-family probabilities and how much each highlighted phrase moved the verdict.</p>
            )
          }
        >
          {!r ? (
            <EmptyInspector text="Pick an example or paste a message. This panel shows the scam probability, the probability of each scam family, and how much each highlighted phrase moved the verdict." />
          ) : (
            <>
              <InspectorSection title="AI-2 verdict" chip={<OutputChip type="model" />}>
                <ProbabilityMeter
                  p={r.p_scam}
                  label="Calibrated scam probability"
                  marks={[
                    { at: 0.3, label: "likely safe below" },
                    { at: 0.7, label: "likely scam above" },
                  ]}
                />
                <KV rows={[["State", r.state.replace(/_/g, " ")], ["Instructions aimed at AI", r.contains_ai_instructions ? "detected" : "none"]]} />
              </InspectorSection>
              <InspectorSection title="Scam family probabilities">
                <div className="space-y-2">
                  {r.top_families.map((f) => (
                    <div key={f.family} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>{f.family.replace(/_/g, " ")}</span>
                        <span className="num font-mono">{pct(f.probability)}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted">
                        <div className="h-full rounded-full bg-foreground/70" style={{ width: `${f.probability * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </InspectorSection>
              <InspectorSection title="Phrase occlusion" chip={<OutputChip type="model">Faithful highlight</OutputChip>}>
                <p className="text-sm text-muted-foreground">Each phrase was removed in turn; the drop is how much the scam probability fell without it.</p>
                <KV rows={r.highlights.map((h) => [h.phrase, `−${(h.drop * 100).toFixed(1)} pts`] as [string, string])} />
              </InspectorSection>
              <TraceFooter trace={r.trace_id} model={r.model_version} data={r.data_version} />
            </>
          )}
        </Inspector>
      }
    />
  );
}
