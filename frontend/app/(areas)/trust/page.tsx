"use client";

import { AlertTriangle, CheckCircle2, ChevronDown, CircleDashed } from "lucide-react";
import { motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { AreaIntro } from "@/components/customer/phone";
import { NotebookFigures } from "@/components/trust/figures";
import { Guard } from "@/components/shell/states";
import { num, tk } from "@/lib/format";
import type { MetricsSummary } from "@/lib/types";
import { usePublic } from "@/lib/use-api";
import { cn } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any -- metric files are free-form JSON written by the notebooks */
type J = any;

const f3 = (v: unknown, d = 3) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(d) : "—");
const p1 = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? `${(v * 100).toFixed(1)}%` : "—");

const NOTEBOOK: Record<string, string> = { ai1: "NB01", ai2: "NB02", ai3: "NB03", ai4: "NB04", ai5: "NB05", ai6: "NB06", ai7: "NB07" };

function SourceBadge({ s, nb }: { s?: string; nb: string }) {
  if (s === "official")
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-volt-ink/50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-volt-ink dark:border-volt/40 dark:text-volt">
        <CheckCircle2 className="size-3" /> {nb} · Kaggle run
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-faint">
      <CircleDashed className="size-3" /> {nb} · {s === "dev" ? "local build, Kaggle run pending" : "not measured yet"}
    </span>
  );
}

function Section({ id, title, ai, src, children, lead }: { id: string; title: string; ai?: string; src?: string; children: ReactNode; lead?: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-border py-12">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          {ai && <p className="label-mono">{ai}</p>}
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h2>
          {lead && <p className="mt-2 max-w-3xl text-sm text-muted-foreground">{lead}</p>}
        </div>
        {ai && <SourceBadge s={src} nb={NOTEBOOK[ai.toLowerCase().replace("-", "")] ?? ""} />}
      </div>
      <div className="mt-6 space-y-6">{children}</div>
    </section>
  );
}

function Table({ cols, rows, highlight, open }: { cols: string[]; rows: ReactNode[][]; highlight?: number; open?: boolean }) {
  const [show, setShow] = useState(open ?? true);
  if (!show)
    return (
      <button
        onClick={() => setShow(true)}
        className="flex w-full items-center justify-between rounded-2xl border border-dashed border-border px-4 py-3 text-left text-sm hover:border-foreground/40"
      >
        <span>
          <span className="font-medium">{cols[0]}</span>
          <span className="text-muted-foreground"> · {rows.length} rows</span>
        </span>
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          Show the table <ChevronDown className="size-3.5" />
        </span>
      </button>
    );
  return (
    <div className="overflow-x-auto rounded-2xl border border-border">
      <table className="w-full min-w-[320px] text-sm">
        <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
          <tr>
            {cols.map((c, i) => (
              <th key={c} className={cn("px-2.5 py-2 font-normal sm:px-3", i > 0 && "text-right")}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((r, i) => (
            <tr key={i} className={cn(highlight === i && "bg-volt/10")}>
              {r.map((c, j) => (
                <td key={j} className={cn("px-2.5 py-2 sm:px-3", j > 0 && "num text-right font-mono text-xs sm:text-[13px]")}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Bars({ rows, max = 1 }: { rows: [string, number][]; max?: number }) {
  return (
    <div className="space-y-2">
      {rows.map(([k, v]) => (
        <div key={k} className="grid grid-cols-[minmax(0,9rem)_1fr_3rem] items-center gap-3 text-sm sm:grid-cols-[minmax(0,14rem)_1fr_3.5rem]">
          <span className="truncate font-mono text-xs">{k}</span>
          <div className="h-1.5 rounded-full bg-muted">
            <div className="h-full rounded-full bg-foreground/70" style={{ width: `${Math.min(100, (v / max) * 100)}%` }} />
          </div>
          <span className="num text-right font-mono text-xs">{f3(v)}</span>
        </div>
      ))}
    </div>
  );
}

const LIMITS = [
  "All data is synthetic. The results show the method works end to end; they are not real-world accuracy.",
  "Scam patterns were designed by the team, so the models may find them easier than real scams. Honest look-alikes, label noise and a leakage guard reduce, but do not remove, this risk.",
  "Dispute deadlines follow Bangladesh Bank’s Bangla QR guideline (27 Sep 2026) as reported by two newspapers; all eight limits match both reports, but the circular’s own text was not checked.",
  "Fee leakage uses an assumed cash-out fee of 1.5%, inside the publicly listed 2026 charges of 1.30–1.85%; it is an estimate for the synthetic world, not a reported figure.",
  "Agent cash on hand is an assumption (1.5 × average daily cash-out) because real float data is not available.",
  "Gemini rewrites facts only; when it is unavailable or a check fails, a template is shown. Only synthetic data is ever sent to it.",
  "Holds and account actions always need a person. The customer is never blocked by the model.",
];

export default function TrustCenter() {
  const q = usePublic<MetricsSummary>("/metrics/summary");

  return (
    <div className="mx-auto max-w-[1760px] px-4 py-8 md:px-8 xl:px-12 md:py-12">
      <AreaIntro
        label="Trust Center · for judges, reviewers and auditors"
        title={
          <>
            Every number, <span className="italic">and where it came from</span>.
          </>
        }
        text="Read live from the result files the notebooks wrote. A green badge means the number comes from the official Kaggle run; a dashed badge means a local build is shown until that notebook is run."
      />
      <Guard q={{ ...q, reload: () => location.reload() }}>
        {(m) => {
          const P = m.per_ai as Record<string, J>;
          const S = m.sources;
          const a1 = P.ai1;
          const t1 = a1?.test_unseen_customers;
          const a2 = P.ai2;
          const a3 = P.ai3;
          const a4 = P.ai4;
          const a5 = P.ai5?.test;
          const a6 = P.ai6;
          const a7 = P.ai7;
          const dc = m.data_card as J;
          return (
            <div className="mt-10">
              <div className="mb-10 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
                {(
                  [
                    ["AI-1", "ai1", t1?.model?.at_5pct_alert_rate?.recall, "scams caught at 5%", "pct"],
                    ["AI-2", "ai2", Math.max(0, ...((a2?.test_heldout_style_B as J[]) ?? []).map((r) => r.verdict_pr_auc ?? 0)), "PR-AUC, unseen style", "num"],
                    ["AI-3", "ai3", (a3?.backtest as J[] | undefined)?.find((r) => r.split === "test" && r.model === a3?.winner_on_validation)?.coverage_80, "80% band coverage", "num"],
                    a4?.cash_to_hold_test
                      ? ["AI-4", "ai4", a4.cash_to_hold_test.forecast_q90?.days_short_of_cash, `days short of cash (usual cash: ${Math.round((a4.cash_to_hold_test.usual_cash?.days_short_of_cash ?? 0) * 100)}%)`, "pct"]
                      : ["AI-4", "ai4", (a4?.backtest as J[] | undefined)?.find((r) => r.split === "test" && r.model === a4?.winner_on_validation)?.coverage_80, "80% band coverage", "num"],
                    ["AI-5", "ai5", a5?.weekly_precision_at_k, "top-20 precision", "pct"],
                    ["AI-6", "ai6", a6?.linking?.analyst_items_reduction, "fewer analyst items", "pct"],
                    ["AI-7", "ai7", a7?.injection_shown_success_rate, "injections shown", "pct"],
                  ] as [string, string, unknown, string, string][]
                ).map(([id, key, v, label, kind], i) => (
                  <motion.a
                    key={id}
                    href={`#${key === "ai3" || key === "ai4" ? "ai34" : key}`}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex flex-col justify-between gap-4 rounded-3xl border border-border bg-card p-4 transition-colors hover:border-foreground/40"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs">{id}</span>
                      <span className={cn("size-2 rounded-full", S[key] === "official" ? "bg-volt-ink dark:bg-volt" : "border border-dashed border-faint")} title={S[key]} />
                    </div>
                    <div>
                      <p className="num font-mono text-2xl font-semibold">{typeof v === "number" ? (kind === "pct" ? `${Math.round(v * 100)}%` : v.toFixed(2)) : "—"}</p>
                      <p className="text-[11px] leading-tight text-muted-foreground">{label}</p>
                    </div>
                  </motion.a>
                ))}
              </div>
              <nav className="no-scrollbar flex gap-2 overflow-x-auto pb-6" aria-label="Sections">
                {[
                  ["data", "Data"],
                  ["ai1", "AI-1"],
                  ["fair", "Fairness"],
                  ["ai2", "AI-2"],
                  ["ai34", "AI-3 · AI-4"],
                  ["ai5", "AI-5"],
                  ["ai6", "AI-6"],
                  ["ai7", "AI-7"],
                  ["health", "Live health"],
                  ["limits", "Limitations"],
                ].map(([id, l]) => (
                  <a key={id} href={`#${id}`} className="shrink-0 rounded-full border border-border px-3 py-1 text-sm text-muted-foreground hover:text-foreground">
                    {l}
                  </a>
                ))}
              </nav>

              <Section id="data" title="The synthetic world (NB00)" lead="One seeded world feeds every notebook. Scammers follow hidden processes; honest look-alikes and 10% label noise keep the task from being trivial.">
                {dc?.meta && (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                    {[
                      ["Events", num(dc.meta.n_events)],
                      ["Days", num(dc.meta.days)],
                      ["Scam transfers", num(dc.meta.n_scam_transfers)],
                      ["Mule wallets", num(dc.meta.n_mules)],
                      ["Disguised QR shops", num(dc.meta.n_disguised_merchants)],
                      ["Seed", String(dc.meta.seed)],
                    ].map(([k, v]) => (
                      <div key={k} className="rounded-2xl border border-border bg-card p-4">
                        <p className="text-xs text-muted-foreground">{k}</p>
                        <p className="num mt-1 font-mono text-xl font-semibold">{v}</p>
                      </div>
                    ))}
                  </div>
                )}
                {a1?.leakage_single_feature_auc && (
                  <div>
                    <p className="mb-3 text-sm font-medium">Leakage guard: no single signal may separate scams on its own (AUC must stay ≤ 0.80)</p>
                    <Bars rows={(a1.leakage_single_feature_auc as J[]).slice(0, 6).map((r) => [r.feature, r.auc])} />
                  </div>
                )}
              </Section>

              <Section
                id="ai1"
                ai="AI-1"
                src={S.ai1}
                title="Pause Check"
                lead="Test = customers never seen in training (grouped split) in the weeks after training. Thresholds and calibration were frozen on validation weeks."
              >
                {t1 && (
                  <Table
                    open
                    cols={["Metric", "UVERA AI-1", "Rule baseline"]}
                    highlight={2}
                    rows={[
                      ["PR-AUC (95% CI)", `${f3(t1.model.pr_auc)} (${f3(t1.model.pr_auc_ci95?.[0], 2)}–${f3(t1.model.pr_auc_ci95?.[1], 2)})`, f3(t1.rule_baseline.pr_auc)],
                      ["ROC-AUC", f3(t1.model.roc_auc), f3(t1.rule_baseline.roc_auc)],
                      ["Recall at a 5% alert rate", p1(t1.model.at_5pct_alert_rate?.recall), p1(t1.rule_baseline.at_5pct_alert_rate?.recall)],
                      ["Precision at a 5% alert rate", p1(t1.model.at_5pct_alert_rate?.precision), p1(t1.rule_baseline.at_5pct_alert_rate?.precision)],
                      ["Scam money caught at 5%", tk(t1.model.at_5pct_alert_rate?.amount_caught), tk(t1.rule_baseline.at_5pct_alert_rate?.amount_caught)],
                      ["False alerts per 1,000 at the pause threshold", f3(t1.model.false_alerts_per_1000_at_red, 1), f3(t1.rule_baseline.false_alerts_per_1000, 1)],
                      ["Calibration error (ECE)", f3(t1.model.ece_calibrated, 4), "—"],
                      ["Test transfers · scams", `${num(t1.n)} · ${num(t1.positives)}`, ""],
                    ]}
                  />
                )}
                {t1?.conformal && (
                  <Table
                    cols={["Conformal coverage (target 90%)", "Coverage", "95% CI"]}
                    rows={[
                      ["Overall", p1(t1.conformal.overall), ""],
                      ["Scam transfers", p1(t1.conformal.class_1), `${p1(t1.conformal.class_1_ci95?.[0])} – ${p1(t1.conformal.class_1_ci95?.[1])}`],
                      ["Normal transfers", p1(t1.conformal.class_0), `${p1(t1.conformal.class_0_ci95?.[0])} – ${p1(t1.conformal.class_0_ci95?.[1])}`],
                      ["Shown as “not sure” to customers", p1(t1.unsure_rate), ""],
                    ]}
                  />
                )}
                {a1?.model_selection && (
                  <div className="rounded-2xl border border-border bg-card p-4 text-sm">
                    <p className="font-medium">Model choice (rule fixed before testing)</p>
                    <p className="mt-1 text-muted-foreground">{a1.model_selection.reason}</p>
                  </div>
                )}
                {a1?.cv_paired_vs_lightgbm && (
                  <Table
                    open={false}
                    cols={["Compared with LightGBM (25 paired CV folds)", "Mean PR-AUC difference", "95% CI", "Folds won"]}
                    rows={(a1.cv_paired_vs_lightgbm as J[]).map((r) => [
                      r.model.replace(/_/g, " "),
                      `${r.mean_diff >= 0 ? "+" : ""}${f3(r.mean_diff, 4)}`,
                      `${f3(r.ci95?.[0], 4)} to ${f3(r.ci95?.[1], 4)}`,
                      `${r.wins}/${r.n_pairs}`,
                    ])}
                  />
                )}
                <div className="grid gap-6 md:grid-cols-2">
                  {a1?.ablation_validation && (
                    <div>
                      <p className="mb-3 text-sm font-medium">Ablation: which signal groups matter (validation PR-AUC)</p>
                      <Bars rows={(a1.ablation_validation as J[]).map((r) => [r.features, r.val_pr_auc])} />
                    </div>
                  )}
                  {a1?.global_importance && (
                    <div>
                      <p className="mb-3 text-sm font-medium">Global importance (mean |TreeSHAP|)</p>
                      <Bars rows={(a1.global_importance as [string, number][]).slice(0, 8)} max={Math.max(...(a1.global_importance as [string, number][]).map((x) => x[1]))} />
                    </div>
                  )}
                </div>
                <NotebookFigures prefix={["ai1_", "summary_"]} />
              </Section>

              <Section id="fair" title="Fairness slices" lead="Error rates by group on the test window. Large gaps would be flagged here; they are shown even when they are not flattering.">
                <Table
                  cols={["AI · slice · group", "n", "False-positive rate", "Missed scams (FNR)", "ECE"]}
                  rows={(m.summary.fairness as J[])
                    .filter((r) => r.ai === "AI-1")
                    .map((r) => [`${r.ai} · ${String(r.slice).replace(/_/g, " ")} · ${r.group}`, num(r.n), p1(r.fpr_at_red), p1(r.fnr_at_red), f3(r.ece, 4)])}
                />
                <div className="grid gap-6 md:grid-cols-2">
                  <Table
                    cols={["AI-5 · shop size", "Honest shops flagged"]}
                    rows={(m.summary.fairness as J[]).filter((r) => r.ai === "AI-5").map((r) => [r.group, p1(r.fpr)])}
                  />
                  <Table
                    cols={["AI-2 · language (served model)", "n", "Verdict PR-AUC", "F1 at 0.5"]}
                    rows={(m.summary.fairness as J[]).filter((r) => r.ai === "AI-2").map((r) => [r.group, num(r.n), f3(r.verdict_pr_auc), f3(r["verdict_f1_at_0.5"])])}
                  />
                </div>
              </Section>

              <Section
                id="ai2"
                ai="AI-2"
                src={S.ai2}
                title="Scam Text Check"
                lead={`Tested on a writing style held out from training (style B). Embedder: ${a2?.embedder ?? "—"}. Best on cross-validation: ${a2?.served_model_chosen_on_cv ?? "—"}. The live demo serves the TF-IDF model: it runs on a free CPU server and its scam / not-scam verdict held up best on the unseen style; the embedding models name the scam family better.`}
              >
                {a2?.test_heldout_style_B && (
                  <Table
                    cols={["Model", "Verdict PR-AUC", "Macro F1 (families)", "ECE", "Uncertainty flags errors (AUROC)"]}
                    rows={(a2.test_heldout_style_B as J[]).map((r) => [r.model.replace(/_/g, " "), f3(r.verdict_pr_auc), f3(r.macro_f1), f3(r.verdict_ece), f3(r.uncertainty_flags_errors_auroc)])}
                  />
                )}
                {a2?.external_uci_sms_spam && typeof a2.external_uci_sms_spam === "object" && (
                  <Table
                    open={false}
                    cols={["External sanity test: UCI SMS Spam (English)", "n", "Spam share", "PR-AUC"]}
                    rows={Object.entries(a2.external_uci_sms_spam as Record<string, J>).map(([k, v]) => [k.replace(/_/g, " "), num(v.n), p1(v.spam_share), f3(v.verdict_pr_auc)])}
                  />
                )}
                <NotebookFigures prefix={["ai2_"]} />
              </Section>

              <Section id="ai34" title="Cash-Flow Guardian and Liquidity Copilot" lead="Rolling-origin backtests against a seasonal-naive baseline. Coverage of the 80% band should be close to 0.80.">
                <div className="grid gap-6 lg:grid-cols-2">
                  {[
                    ["AI-3", a3, S.ai3],
                    ["AI-4", a4, S.ai4],
                  ].map(([name, a, s]) => (
                    <div key={name as string} className="space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-medium">
                          {name as string} · winner on validation: {(a as J)?.winner_on_validation ?? "—"}
                        </p>
                        <SourceBadge s={s as string} nb={name === "AI-3" ? "NB03" : "NB04"} />
                      </div>
                      {(a as J)?.backtest && (
                        <Table
                          cols={["Test split · model", "MASE", "Pinball", "80% coverage"]}
                          rows={((a as J).backtest as J[])
                            .filter((r) => r.split === "test")
                            .map((r) => [String(r.model).replace(/_/g, " "), f3(r.mase), f3(r.pinball_mean, 0), f3(r.coverage_80, 2)])}
                        />
                      )}
                      {(() => {
                        const pr = name === "AI-3" ? (a as J)?.shortfall_probability_test : (a as J)?.stockout_probability_test;
                        if (!pr) return null;
                        return (
                          <Table
                            cols={[name === "AI-3" ? "Shortfall probability (test)" : "Stock-out probability (test)", "Model", "History baseline"]}
                            rows={[
                              ["Brier score (lower is better)", f3(pr.brier), f3(pr.brier_baseline)],
                              ["PR-AUC", f3(pr.pr_auc), f3(pr.pr_auc_baseline)],
                              ["Calibration error", f3(pr.ece), ""],
                            ]}
                          />
                        );
                      })()}
                      {name === "AI-4" && (a as J)?.cash_to_hold_test && (() => {
                        const c = (a as J).cash_to_hold_test as J;
                        const row = (label: string, r?: J) =>
                          r ? [label, `${(r.days_short_of_cash * 100).toFixed(1)}%`, tk(r.mean_cash_bdt), r.extra_vs_usual_bdt > 0 ? `+${tk(r.extra_vs_usual_bdt)}` : "—"] : null;
                        return (
                          <>
                            <Table
                              cols={["Cash to hold (test weeks)", "Days short of cash", "Mean cash", "Extra"]}
                              highlight={1}
                              rows={[
                                row("Usual cash on hand", c.usual_cash),
                                row("Hold the 90% forecast (UVERA)", c.forecast_q90),
                                row("Same extra cash, spread flat", c.same_extra_cash_spread_flat),
                                row("Seasonal-naive 90% level", c.seasonal_naive_q90),
                              ].filter(Boolean) as string[][]}
                            />
                            <p className="text-sm text-muted-foreground">
                              Holding the 90% forecast cuts days without enough cash from about one in five to one in eight. A flat top-up with the
                              same total cash does about as well, so in this synthetic world the value is in sizing the buffer, not in predicting
                              which day runs short; that is why the agent page flags no single day.
                            </p>
                          </>
                        );
                      })()}
                    </div>
                  ))}
                </div>
                <NotebookFigures prefix={["ai3_", "ai4_"]} />
              </Section>

              <Section id="ai5" ai="AI-5" src={S.ai5} title="QR Shield" lead="Test weeks, merchants never seen in training. Scheme D (rotating ring) was held out completely to test unseen patterns.">
                {a5 && (
                  <>
                    <Table
                      cols={["Metric", "Value"]}
                      rows={[
                        ["PR-AUC (seen schemes)", f3(a5.pr_auc_seen_families)],
                        ["Precision of the weekly top 20", p1(a5.weekly_precision_at_k)],
                        ["Peer z-score baseline PR-AUC", f3(a5.peer_z_baseline_pr_auc)],
                        ["Honest round-price shops flagged", p1(a5.fpr_honest_round_price_shops)],
                        ["All honest shops flagged", p1(a5.fpr_honest_all)],
                        ["Unseen scheme D, fused PR-AUC", f3(a5.unseen_family_D?.fused)],
                        ["Calibration error", f3(a5.ece)],
                      ]}
                    />
                    {a5.recall_by_family && (
                      <div>
                        <p className="mb-3 text-sm font-medium">Recall by cash-out scheme</p>
                        <Bars rows={Object.entries(a5.recall_by_family as Record<string, number>)} />
                      </div>
                    )}
                  </>
                )}
                <NotebookFigures prefix={["ai5_"]} />
              </Section>

              <Section id="ai6" ai="AI-6" src={S.ai6} title="Case Linker" lead={a6?.method}>
                {a6?.linking && (
                  <Table
                    cols={["Metric", "Value"]}
                    rows={[
                      ["Alerts → cases", `${num(a6.linking.n_alerts)} → ${num(a6.linking.n_cases)}`],
                      ["Fewer items for analysts", p1(a6.linking.analyst_items_reduction)],
                      ["Alert pairs with the same mule correctly linked", p1(a6.linking.same_mule_pairs_linked)],
                      ["Case purity (one true ring per case)", p1(a6.linking.case_purity_mean)],
                      ["Cash-out points found for detected cases", p1(a6.linking.cashouts_found_for_detected_cases)],
                    ]}
                  />
                )}
                {a6?.score_formula && <p className="font-mono text-xs text-muted-foreground">Case score = {a6.score_formula}</p>}
              </Section>

              <Section id="ai7" ai="AI-7" src={S.ai7} title="Grounded Brief" lead={`LLM: ${a7?.llm ?? "—"} · retrieval: ${a7?.retrieval ?? "—"}`}>
                {a7 && (
                  <Table
                    cols={["Metric", "Value"]}
                    rows={[
                      ["LLM outputs passing the validator", p1(a7.validator_pass_rate_llm)],
                      ["Template fallback rate", p1(a7.fallback_rate)],
                      ["Shown text that is valid", p1(a7.shown_text_valid_rate)],
                      ["Prompt-injection success (raw LLM)", p1(a7.injection_raw_success_rate)],
                      ["Prompt-injection success (shown to users)", p1(a7.injection_shown_success_rate)],
                      ["Injection tests", num(a7.n_injection_tests)],
                    ]}
                  />
                )}
              </Section>

              <Section id="health" title="Live system health" lead="Measured by this running API since it started.">
                <Table
                  open={false}
                  cols={["Route", "Requests", "p50 ms", "p95 ms"]}
                  rows={Object.entries(m.live_health.routes).map(([k, v]) => [k, num(v.n), f3(v.p50_ms, 1), f3(v.p95_ms, 1)])}
                />
                <p className="text-sm text-muted-foreground">
                  Briefs: {Object.entries(m.live_health.briefs).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(" · ")}
                </p>
              </Section>

              <Section id="limits" title="Limitations, stated plainly">
                <ul className="space-y-3">
                  {LIMITS.map((l) => (
                    <li key={l} className="flex gap-3 text-sm">
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-caution" />
                      <span>{l}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-sm text-muted-foreground">{m.note}</p>
              </Section>
            </div>
          );
        }}
      </Guard>
    </div>
  );
}
