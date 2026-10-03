/** Shapes returned by the UVERA API (backend/app/api/v1). Every response carries the envelope fields. */

export type Envelope = {
  trace_id: string;
  model_version: string;
  data_version: string;
  api_version: string;
  generated_at: string;
  degraded: boolean;
  degraded_reason: string | null;
  synthetic_data: boolean;
};

export type Persona = { name: string; role: string; id: string; zone?: string; language?: string; tenure_days?: number; story: string };

export type PauseRequest = {
  sender_id: string;
  recipient_wallet: string;
  amount: number;
  hour: number;
  channel: "app" | "ussd";
  note?: string;
  simulated_context?: { minutes_since_cash_in?: number; device_changed_recently?: boolean; pin_reset_recently?: boolean };
};

export type Scenario = {
  id: string;
  title: string;
  area: "customer" | "customer_text" | "customer_guardian" | "agent" | "ops" | "ops_qr";
  story?: string;
  request: Record<string, unknown>;
  links?: { case?: string; agent?: string; merchant?: string };
  p_shortfall?: number;
};

export type Demo = Envelope & { personas: Record<string, Persona>; scenarios: Scenario[] };

export type Reason = { feature: string; value: number; contribution: number; text_en: string; text_bn: string };

export type TextCheck = {
  model_version: string;
  p_scam: number;
  state: "likely_scam" | "likely_safe" | "unsure";
  family: string;
  family_text_en: string;
  family_text_bn: string;
  top_families: { family: string; probability: number }[];
  highlights: { phrase: string; drop: number; start_word: number }[];
  contains_ai_instructions: boolean;
  note: string;
};

export type Brief = { bangla: string; english: string; card_ids: string[]; evidence_ids: string[]; source: string };

export type PauseResult = Envelope & {
  model_score: number;
  calibrated_probability: number;
  conformal_set: string[];
  ood_flag: boolean;
  risk_level: "low" | "medium" | "high";
  uncertainty_state: "confident" | "unsure";
  state: string;
  recommendation: string[];
  human_review: string;
  reasons_for_unsure: string[];
  reasons: Reason[];
  /** null when the draft is already low risk (nothing to lower) */
  counterfactual: { amount_bdt: number | null; text_en: string; text_bn: string } | null;
  thresholds: { amber_p: number; red_p: number };
  rule_hits: { id: string; type: string; text: string }[];
  note_check: TextCheck | null;
  brief: Brief;
  evidence_ids: string[];
  inputs: { amount: number; hour: number; channel: string; simulated_context: Record<string, unknown> | null };
  key_facts: { recipient_age_days: number; first_time_pair: boolean; receiver_senders_7d: number; share_of_balance: number };
};

export type Profile = Envelope & {
  customer_id: string;
  display_name: string;
  zone: string;
  channel: string;
  language: string;
  tenure_days: number;
  balance_bdt: number;
  today: string;
  recent: { time: string; type: string; direction: "in" | "out"; counterparty: string; amount: number }[];
};

export type Band = { date: string; q10: number; q50: number; q90: number };

export type SavingsPlan = { plan: string; monthly_bdt: number; months_to_goal: number | null; meets_deadline: boolean };

export type Cashflow = Envelope & {
  customer_id: string;
  model: string;
  validated_winner: string;
  source: string;
  balance_now_bdt: number;
  floor_bdt: number;
  history: { date: string; net: number; inflow: number; outflow: number; balance: number }[];
  forecast: Band[];
  p_shortfall_7d: number;
  probability_method: string;
  warning_threshold: number;
  warning: boolean;
  event: string;
  heavy_outflow_weeks: { week_start: string; outflow_bdt: number }[];
  monthly_free_cash: { q10: number; q50: number };
  savings_plans: SavingsPlan[];
};

export type Peers = {
  n: number;
  median_daily_cash_out: number;
  p25: number;
  p75: number;
  mine_last_28d: number;
  mine_previous_28d: number;
  change_pct: number;
};

export type Liquidity = Envelope & {
  agent_id: string;
  display_name: string;
  zone: string;
  size: string;
  model: string;
  validated_winner: string;
  source: string;
  capacity_bdt: number;
  guidance: string;
  event: string;
  history: { date: string; cash_out: number; cash_in: number }[];
  forecast: (Band & { weekday: string; p_stockout: number; cash_to_hold_90pct_bdt: number; topup_bdt: number; highlight: boolean })[];
  peers: Peers;
};

export type Area = Envelope & {
  agent_id: string;
  zone: string;
  qr: {
    zone: string;
    weeks: { week: number; flagged_merchants: number; est_fee_leakage_bdt: number }[];
    latest: { zone: string; week: number; flagged_merchants: number; est_fee_leakage_bdt: number; merchants: number };
    note: string;
  };
  peers: Peers;
};

export type Deadline = {
  rule: string;
  label: string;
  limit: number;
  unit: string;
  due: string;
  remaining_hours: number;
  remaining_fraction: number;
  status: "ok" | "soon" | "urgent" | "breached" | string;
};

export type CaseRow = {
  case_key: string;
  score: number;
  n_alerts: number;
  victims: number;
  wallets: number;
  merchants: number;
  agents: number;
  amount_at_risk_bdt: number;
  qr_flagged_endpoint: boolean;
  opened: string;
  opened_hours_ago: number;
  latest_complaint: string;
  latest_complaint_hours_ago: number;
  next_deadline: Deadline | null;
  breached: number;
  priority: number;
  status: string;
};

export type Cases = Envelope & { cases: CaseRow[]; total: number; now: number };

export type GraphNode = { id: string; type: string; role: string; qr_state: string | null };
export type GraphEdge = { id: string; source: string; target: string; type: string; amount: number; hop: number; time: string };

export type CaseDetail = Envelope &
  CaseRow & {
    evidence: { id: string; type: string; text: string; value: number }[];
    victim_ids: string[];
    wallet_ids: string[];
    merchant_ids: string[];
    agent_ids: string[];
    forwarded_share: number;
    graph: { nodes: GraphNode[]; edges: GraphEdge[] };
    dispute_clock: Deadline[];
    dispute_rules_verified: boolean;
    dispute_rules_note: string;
    brief: Brief;
    actions: { action: string; reason: string; actor_role: string; actor_id: string; at: number }[];
  };

export type QrState = "green" | "amber" | "red" | "grey_review";

export type QrMerchant = {
  merchant_id: string;
  zone: string;
  category: string;
  size: string;
  week: number;
  state: QrState;
  p_calibrated: number;
  payments: number;
  volume_bdt: number;
  est_fee_leakage_bdt: number;
  components: { supervised: number; isolation_forest: number; peer_z: number };
  reasons: Reason[];
  recommended_actions: string[];
};

export type QrList = Envelope & { merchants: QrMerchant[]; counts: Record<string, number> };

export type QrDetail = Envelope &
  QrMerchant & {
    history: { week: number; state: QrState; p_calibrated: number }[];
    peer_comparison: { metric: string; this_shop: number; peer_median: number; peer_p90: number }[];
    peers_n: number;
    fee_assumption: { fee_rate: number; verified: boolean; note: string };
  };

export type WorldSample = {
  note: string;
  nodes: { id: string; type: "customer" | "agent" | "merchant" | "case" | "external"; layer: number; flag: string | null }[];
  edges: { source: string; target: string; type: string; amount: number; scam: boolean; case: number | null }[];
};

type NM = number | string;

export type MetricsSummary = Envelope & {
  summary: {
    available: Record<string, boolean>;
    headline: {
      ai1: {
        pr_auc: NM;
        pr_auc_rule_baseline: NM;
        recall_at_5pct_alert_rate: NM;
        recall_at_5pct_rule_baseline: NM;
        false_alerts_per_1000: NM;
        ece: NM;
        conformal_coverage: { overall: number; class_1: number; class_0: number; unsure_rate: number; target: number } | string;
        unsure_rate: NM;
        error_at_80pct_coverage: NM;
        error_at_100pct_coverage: NM;
        loss_prevented_bdt: Record<string, { model: number; rule_baseline: number; follow_rate: number }> | string;
      };
      ai2: { served_model: string; embedder: string; heldout_style_verdict_pr_auc: NM; heldout_macro_f1: NM; external_uci: unknown };
      ai3: { winner: string; shortfall: Record<string, unknown> | string };
      ai4: { winner: string; stockout: Record<string, unknown> | string };
      ai5: { pr_auc_seen: NM; precision_at_k: NM; unseen_family_D: unknown; fpr_honest_round_price: NM; fpr_honest_all: NM };
      ai6: Record<string, NM> | string;
      ai7: Record<string, NM>;
    };
    fairness: Record<string, unknown>[];
    note: string;
  };
  per_ai: Record<string, Record<string, unknown> | null>;
  data_card: { meta: Record<string, unknown> } & Record<string, unknown>;
  sources: Record<string, "official" | "dev" | "missing">;
  live_health: { routes: Record<string, { n: number; p50_ms: number; p95_ms: number }>; counters: Record<string, number>; briefs: Record<string, number> };
  note: string;
};
