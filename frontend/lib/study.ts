"use client";

import { API_BASE } from "./api";

/**
 * On-site user study: content, the synthetic triage alerts, and an upload queue that survives a lost connection.
 * Nothing personal is collected: no names, no phone numbers, no device identifiers.
 */
export const STUDY_VERSION = "s1-2026-10-07";

export type L = "bn" | "en";
export type Bi = { bn: string; en: string };
export type Option<V extends string = string> = { value: V; label: Bi };

export type StudyPayload = {
  study_version: string;
  client_id: string;
  consent: true;
  facilitator?: string | null;
  ui_lang: L;
  assignment?: string;
  started_at?: string;
  total_ms?: number;
  profile: Partial<Record<"age_band" | "mm_use" | "phone_lang" | "scam_contact" | "scam_loss", string>>;
  task1?: {
    lang: L;
    q1_meaning?: string;
    q2_action?: string;
    q3_reason?: string;
    q4_clarity?: number;
    q5_trust?: number;
    q6_annoyance?: number;
    view_ms?: number;
    total_ms?: number;
  };
  task2?: { lang: L; q_next?: string; q_ok_unsure?: number; view_ms?: number; total_ms?: number };
  task3?: { arm: "A" | "B"; rings?: number; first_wallet?: string; time_ms?: number; confidence?: number };
  comment?: string | null;
};

// ---------------------------------------------------------------- profile questions

export const PROFILE: { key: keyof StudyPayload["profile"]; q: Bi; options: Option[] }[] = [
  {
    key: "age_band",
    q: { bn: "আপনার বয়স কত?", en: "How old are you?" },
    options: ["18-24", "25-34", "35-44", "45+"].map((v) => ({ value: v, label: { bn: v.replace("-", "–"), en: v.replace("-", "–") } })),
  },
  {
    key: "mm_use",
    q: { bn: "আপনি কত ঘন ঘন মোবাইল ব্যাংকিং (MFS) ব্যবহার করেন?", en: "How often do you use mobile money (MFS)?" },
    options: [
      { value: "daily", label: { bn: "প্রতিদিন", en: "Every day" } },
      { value: "weekly", label: { bn: "প্রতি সপ্তাহে", en: "Every week" } },
      { value: "rarely", label: { bn: "খুব কম", en: "Rarely" } },
      { value: "never", label: { bn: "কখনো না", en: "Never" } },
    ],
  },
  {
    key: "phone_lang",
    q: { bn: "ফোনে আপনি মূলত কোন ভাষা ব্যবহার করেন?", en: "Which language do you mostly use on your phone?" },
    options: [
      { value: "bn", label: { bn: "বাংলা", en: "Bangla" } },
      { value: "en", label: { bn: "ইংরেজি", en: "English" } },
      { value: "both", label: { bn: "দুটোই", en: "Both" } },
    ],
  },
  {
    key: "scam_contact",
    q: { bn: "আপনি কি কখনো প্রতারণার এসএমএস বা কল পেয়েছেন?", en: "Have you ever received a scam SMS or call?" },
    options: [
      { value: "yes", label: { bn: "হ্যাঁ", en: "Yes" } },
      { value: "no", label: { bn: "না", en: "No" } },
      { value: "not_sure", label: { bn: "নিশ্চিত নই", en: "Not sure" } },
    ],
  },
  {
    key: "scam_loss",
    q: { bn: "আপনি কি কখনো প্রতারণায় টাকা হারিয়েছেন?", en: "Have you ever lost money to a scam?" },
    options: [
      { value: "yes", label: { bn: "হ্যাঁ", en: "Yes" } },
      { value: "no", label: { bn: "না", en: "No" } },
      { value: "prefer_not", label: { bn: "বলতে চাই না", en: "Prefer not to say" } },
    ],
  },
];

// ---------------------------------------------------------------- task 1 and 2 questions

export const T1_MEANING: Option[] = [
  { value: "paused_scam", label: { bn: "লেনদেনটি প্রতারণা হতে পারে, তাই থামানো হয়েছে", en: "The transfer may be a scam, so it is paused" } },
  { value: "failed", label: { bn: "লেনদেনটি ব্যর্থ হয়েছে", en: "The transfer failed" } },
  { value: "blocked", label: { bn: "আমার অ্যাকাউন্ট বন্ধ করে দেওয়া হয়েছে", en: "My account is blocked" } },
];
export const NOT_SURE: Option = { value: "not_sure", label: { bn: "নিশ্চিত নই", en: "Not sure" } };

export const T1_ACTION: Option[] = [
  { value: "wait", label: { bn: "১০ মিনিট অপেক্ষা করব", en: "Wait 10 minutes" } },
  { value: "verify", label: { bn: "নম্বরটি যাচাই করব", en: "Verify the number" } },
  { value: "ask", label: { bn: "বিশ্বস্ত কাউকে জিজ্ঞেস করব", en: "Ask someone I trust" } },
  { value: "send_anyway", label: { bn: "তবুও পাঠিয়ে দেব", en: "Send anyway" } },
];

export const T1_REASON: Option[] = [
  { value: "senders", label: { bn: "এই সপ্তাহে ১৯ জন এই ওয়ালেটে টাকা পাঠিয়েছে", en: "19 people paid this wallet this week" } },
  { value: "moves_on", label: { bn: "এখানে আসা প্রায় সব টাকা (>৯৯%) দ্রুত বের হয়ে যায়", en: "Almost all money sent here (>99%) moves on quickly" } },
  { value: "wallet_age", label: { bn: "প্রাপকের ওয়ালেটটি মাত্র ১২ দিন পুরোনো", en: "The receiving wallet is only 12 days old" } },
  { value: "none", label: { bn: "কোনোটিই না", en: "None of them" } },
];

export const T2_NEXT: Option[] = [
  { value: "person_checks", label: { bn: "টাকা যাওয়ার আগে একজন কর্মী এটি যাচাই করবেন", en: "A person checks it before the money moves" } },
  { value: "sent", label: { bn: "টাকা পাঠানো হয়ে যাবে", en: "The money is sent" } },
  { value: "lost", label: { bn: "টাকা হারিয়ে যাবে", en: "The money is lost" } },
];

export type ScaleQ = { q: Bi; low: Bi; high: Bi };
export const SCALES = {
  clarity: { q: { bn: "স্ক্রিনটি কতটা পরিষ্কার ছিল?", en: "How clear was this screen?" }, low: { bn: "একদম অস্পষ্ট", en: "Not clear at all" }, high: { bn: "খুব পরিষ্কার", en: "Very clear" } },
  trust: { q: { bn: "আপনি কি এই সতর্কবার্তায় ভরসা করবেন?", en: "Would you trust this warning?" }, low: { bn: "একদমই না", en: "Not at all" }, high: { bn: "পুরোপুরি", en: "Completely" } },
  annoyance: {
    q: { bn: "লেনদেনটি আসলে নিরাপদ হলে, এমন ছোট একটি বিরতি কি আপনাকে বিরক্ত করত?", en: "If the transfer was actually safe, would a short pause like this annoy you?" },
    low: { bn: "একদমই না", en: "Not at all" },
    high: { bn: "খুব বেশি", en: "Very much" },
  },
  okUnsure: {
    q: { bn: "অনুমান না করে অ্যাপটি “নিশ্চিত নয়” বলছে — এটা কি আপনার কাছে ঠিক মনে হয়?", en: "Is it OK that the app says “not sure” instead of guessing?" },
    low: { bn: "একদম ঠিক নয়", en: "Not OK" },
    high: { bn: "পুরোপুরি ঠিক", en: "Completely OK" },
  },
  confidence: { q: { bn: "এই দুটি উত্তরে আপনি কতটা নিশ্চিত?", en: "How sure are you about these two answers?" }, low: { bn: "একদমই না", en: "Not at all" }, high: { bn: "খুব নিশ্চিত", en: "Very sure" } },
} satisfies Record<string, ScaleQ>;

// ---------------------------------------------------------------- task 3: 12 synthetic alerts

/** True structure: 3 rings (5 alerts end in W-77 via three first-hop wallets, 4 alerts go straight to W-31 and are cashed out,
 * 2 alerts end in W-58 via two first-hop wallets) + 1 unrelated alert. In the plain list, W-77 is visible only in the
 * "money went next to" column, while W-31 is the most frequent receiver: simple counting points to the wrong wallet. */
export type Alert = { id: string; time: string; sender: string; receiver: string; next: string; amount: number; risk: number; ring: string };
export const ALERTS: Alert[] = [
  { id: "AL-301", time: "09:02", sender: "C007735", receiver: "W-31", next: "A-512 cash-out", amount: 5500, risk: 0.88, ring: "W-31" },
  { id: "AL-302", time: "09:10", sender: "C004211", receiver: "R-104", next: "W-77", amount: 3000, risk: 0.91, ring: "W-77" },
  { id: "AL-303", time: "09:24", sender: "C002980", receiver: "R-219", next: "W-77", amount: 2500, risk: 0.84, ring: "W-77" },
  { id: "AL-304", time: "09:31", sender: "C006154", receiver: "R-640", next: "W-58", amount: 7000, risk: 0.79, ring: "W-58" },
  { id: "AL-305", time: "09:47", sender: "C001873", receiver: "W-31", next: "A-512 cash-out", amount: 4000, risk: 0.93, ring: "W-31" },
  { id: "AL-306", time: "10:05", sender: "C008402", receiver: "R-104", next: "W-77", amount: 3000, risk: 0.87, ring: "W-77" },
  { id: "AL-307", time: "10:18", sender: "C003369", receiver: "R-915", next: "—", amount: 12000, risk: 0.95, ring: "single" },
  { id: "AL-308", time: "10:26", sender: "C005027", receiver: "W-31", next: "A-512 cash-out", amount: 6000, risk: 0.81, ring: "W-31" },
  { id: "AL-309", time: "10:40", sender: "C009118", receiver: "R-388", next: "W-77", amount: 2000, risk: 0.76, ring: "W-77" },
  { id: "AL-310", time: "10:52", sender: "C004450", receiver: "R-702", next: "W-58", amount: 6500, risk: 0.72, ring: "W-58" },
  { id: "AL-311", time: "11:15", sender: "C002266", receiver: "R-219", next: "W-77", amount: 3500, risk: 0.89, ring: "W-77" },
  { id: "AL-312", time: "11:33", sender: "C007591", receiver: "W-31", next: "A-512 cash-out", amount: 5000, risk: 0.83, ring: "W-31" },
];

export type LinkedCase = { id: string; wallet: string; via: string[]; alerts: Alert[]; deadline: Bi };
export const CASES: LinkedCase[] = [
  { id: "K-2041", wallet: "W-31", via: [], deadline: { bn: "১৮ ঘণ্টা বাকি", en: "18 h left" } },
  { id: "K-2042", wallet: "W-77", via: ["R-104", "R-219", "R-388"], deadline: { bn: "৬ ঘণ্টা বাকি", en: "6 h left" } },
  { id: "K-2043", wallet: "W-58", via: ["R-640", "R-702"], deadline: { bn: "২০ ঘণ্টা বাকি", en: "20 h left" } },
].map((c) => ({ ...c, alerts: ALERTS.filter((a) => a.ring === c.wallet) }));
export const SINGLE = ALERTS.filter((a) => a.ring === "single");

export const WALLET_OPTIONS: Option[] = [
  { value: "W-31", label: { bn: "W-31", en: "W-31" } },
  { value: "R-104", label: { bn: "R-104", en: "R-104" } },
  { value: "W-77", label: { bn: "W-77", en: "W-77" } },
  { value: "W-58", label: { bn: "W-58", en: "W-58" } },
  NOT_SURE,
];

// ---------------------------------------------------------------- assignment (balanced per device)

const BLOCK_KEY = "uvera.study.block";
const FAC_KEY = "uvera.study.facilitator";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* private mode: nothing persists, the study still works */
  }
}

export function shuffle<T>(xs: T[]): T[] {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** Version A/B and the language of the warning screens come from a shuffled block of all four combinations, so a
 * handful of participants on one phone is still balanced across both factors. */
export function nextAssignment(): { arm: "A" | "B"; screenLang: L } {
  let block: string[] = [];
  try {
    block = JSON.parse(read(BLOCK_KEY) ?? "[]");
  } catch {
    block = [];
  }
  if (!Array.isArray(block) || !block.length) block = shuffle(["A-bn", "A-en", "B-bn", "B-en"]);
  const next = block.shift() ?? "A-bn";
  write(BLOCK_KEY, JSON.stringify(block));
  const [arm, lang] = next.split("-");
  return { arm: arm === "B" ? "B" : "A", screenLang: lang === "en" ? "en" : "bn" };
}

export const getFacilitator = () => read(FAC_KEY) ?? "";
export const setFacilitator = (v: string) => write(FAC_KEY, v || null);

export function newId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 14)}`;
  }
}

// ---------------------------------------------------------------- upload with an offline queue

const QUEUE_KEY = "uvera.study.pending.v1";
const qListeners = new Set<() => void>();

export function pendingResponses(): StudyPayload[] {
  try {
    const xs = JSON.parse(read(QUEUE_KEY) ?? "[]");
    return Array.isArray(xs) ? xs : [];
  } catch {
    return [];
  }
}

function savePending(xs: StudyPayload[]) {
  write(QUEUE_KEY, xs.length ? JSON.stringify(xs) : null);
  qListeners.forEach((fn) => fn());
}

export function onQueueChange(fn: () => void) {
  qListeners.add(fn);
  return () => {
    qListeners.delete(fn);
  };
}

async function upload(p: StudyPayload): Promise<"ok" | "retry" | "rejected"> {
  if (!API_BASE) return "retry";
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 10000);
  try {
    const res = await fetch(`${API_BASE}/v1/study/responses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
      signal: ctl.signal,
      cache: "no-store",
    });
    if (res.ok) return "ok";
    return res.status === 422 || res.status === 413 ? "rejected" : "retry";
  } catch {
    return "retry";
  } finally {
    clearTimeout(timer);
  }
}

/** Upload now; if the API cannot be reached, keep the response on this phone and try again later. */
export async function submitResponse(p: StudyPayload): Promise<"sent" | "queued"> {
  const out = await upload(p);
  if (out === "ok") return "sent";
  savePending([...pendingResponses().filter((x) => x.client_id !== p.client_id), p]);
  return "queued";
}

let flushing = false;
/** Try every queued response once. Rejected ones (invalid) stay for the facilitator to export by hand. */
export async function flushQueue(): Promise<number> {
  if (flushing) return pendingResponses().length;
  flushing = true;
  try {
    for (const p of pendingResponses()) {
      const out = await upload(p);
      if (out === "ok") savePending(pendingResponses().filter((x) => x.client_id !== p.client_id));
      if (out === "retry") break; // still offline: stop for now
    }
  } finally {
    flushing = false;
  }
  return pendingResponses().length;
}

export function clearQueue() {
  savePending([]);
}

// ---------------------------------------------------------------- results (team only)

const PIN_KEY = "uvera.study.pin";
export function storedPin(): string {
  try {
    return sessionStorage.getItem(PIN_KEY) ?? "";
  } catch {
    return "";
  }
}
export function storePin(pin: string | null) {
  try {
    if (pin) sessionStorage.setItem(PIN_KEY, pin);
    else sessionStorage.removeItem(PIN_KEY);
  } catch {
    /* private mode */
  }
}

export async function fetchStudy(path: "/study/results" | "/study/export.csv", pin: string): Promise<Response> {
  if (!API_BASE) throw new Error("No live API is configured for this website.");
  return fetch(`${API_BASE}/v1${path}`, { headers: { "X-Study-Pin": pin }, cache: "no-store" });
}
