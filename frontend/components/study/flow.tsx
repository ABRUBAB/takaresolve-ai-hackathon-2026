"use client";

import Link from "next/link";
import { CheckCircle2, ChevronLeft, CloudOff, Eye, EyeOff, Minus, Plus, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { Mark } from "@/components/brand/logo";
import { PauseMock, TriageCases, TriageList, UnsureMock } from "@/components/study/screens";
import {
  clearQueue,
  flushQueue,
  getFacilitator,
  newId,
  nextAssignment,
  NOT_SURE,
  onQueueChange,
  pendingResponses,
  PROFILE,
  SCALES,
  setFacilitator,
  shuffle,
  STUDY_VERSION,
  submitResponse,
  T1_ACTION,
  T1_MEANING,
  T1_REASON,
  T2_NEXT,
  WALLET_OPTIONS,
  type Bi,
  type L,
  type Option,
  type ScaleQ,
  type StudyPayload,
} from "@/lib/study";
import { cn } from "@/lib/utils";

const STEPS = [
  "consent",
  "p_age_band",
  "p_mm_use",
  "p_phone_lang",
  "p_scam_contact",
  "p_scam_loss",
  "t1_view",
  "t1_q1",
  "t1_q2",
  "t1_q3",
  "t1_q4",
  "t1_q5",
  "t1_q6",
  "t2_view",
  "t2_q1",
  "t2_q2",
  "t3_intro",
  "t3_task",
  "t3_conf",
  "comment",
  "done",
] as const;
type Step = (typeof STEPS)[number];

const T = {
  study: { bn: "ব্যবহারকারী পরীক্ষা", en: "User study" },
  next: { bn: "এগিয়ে যান", en: "Next" },
  back: { bn: "ফিরে যান", en: "Back" },
  of: { bn: "ধাপ", en: "Step" },
  consentTitle: { bn: "প্রতারণা-সতর্কবার্তার ৫ মিনিটের একটি পরীক্ষা", en: "A 5-minute test of a scam warning" },
  consentLead: {
    bn: "আমরা UVERA নামে একটি অ্যাপ বানাচ্ছি, যা টাকা পাঠানোর আগে প্রতারণা ধরতে সাহায্য করে। কয়েকটি স্ক্রিন দেখে সহজ কিছু প্রশ্নের উত্তর দিন।",
    en: "We are building UVERA, an app that helps catch scams before money is sent. Look at a few screens and answer some short questions.",
  },
  consent: [
    { bn: "অংশগ্রহণ সম্পূর্ণ স্বেচ্ছায়। যেকোনো সময় থামতে পারেন।", en: "Taking part is voluntary. You can stop at any time." },
    { bn: "এটি বেনামি: আমরা কখনো আপনার নাম বা ফোন নম্বর চাই না।", en: "It is anonymous: we never ask for your name or phone number." },
    { bn: "যা দেখবেন সবই বানানো তথ্যের ডেমো। কোনো আসল টাকা লেনদেন হবে না।", en: "Everything you see is a demo with made-up data. No real money moves." },
    { bn: "আমরা অ্যাপটি পরীক্ষা করছি, আপনাকে নয়। কিছু অস্পষ্ট লাগলে সেটা অ্যাপের দোষ।", en: "We are testing the app, not you. If something is unclear, that is the app's fault." },
    { bn: "উত্তরগুলো নাম ছাড়া সংরক্ষণ করা হয়, শুধু ডিজাইন উন্নত করার জন্য।", en: "Answers are stored without names, only to improve the design." },
  ],
  agree: { bn: "আমি রাজি, শুরু করি", en: "I agree, start" },
  facilitator: { bn: "ফ্যাসিলিটেটর কোড (দলের জন্য, যেমন F1)", en: "Facilitator code (for the team, e.g. F1)" },
  aboutYou: { bn: "আপনার সম্পর্কে", en: "About you" },
  task1: { bn: "কাজ ১ · সতর্কবার্তা", en: "Task 1 · The warning" },
  task1Context: {
    bn: "ধরুন, আপনি এই এসএমএসটি পেলেন:",
    en: "Imagine you received this SMS:",
  },
  sms: {
    bn: "অভিনন্দন! আপনি ৫০,০০০ টাকা জিতেছেন। টাকা পেতে ৩,০০০ টাকা ফি পাঠান।",
    en: "Congratulations! You won Tk 50,000. Send a Tk 3,000 fee to receive it.",
  },
  task1Then: {
    bn: "আপনি এসএমএসের নম্বরে ৩,০০০ টাকা পাঠাতে গেলেন। তখন আপনার ওয়ালেটে এই স্ক্রিনটি এলো:",
    en: "You start sending Tk 3,000 to the number in the SMS. Your wallet then shows this screen:",
  },
  readIt: { bn: "দেখেছি, প্রশ্নে যাই", en: "I have looked at it" },
  showAgain: { bn: "স্ক্রিনটি আবার দেখুন", en: "See the screen again" },
  hide: { bn: "স্ক্রিন লুকান", en: "Hide the screen" },
  q1: { bn: "এই স্ক্রিনটি আপনাকে কী বলছে?", en: "What is this screen telling you?" },
  q2: { bn: "এখন আপনি কী করবেন?", en: "What would you do now?" },
  q3: { bn: "কোন কারণটি আপনাকে সবচেয়ে বেশি সতর্ক করেছে?", en: "Which reason made you most careful?" },
  task2: { bn: "কাজ ২ · “নিশ্চিত নয়”", en: "Task 2 · “Not sure”" },
  task2Context: {
    bn: "আরেকটি ঘটনা। গতকাল আপনি নতুন ফোন নিয়েছেন এবং পিন রিসেট করেছেন। আজ রাত ১১টায় আপনি ৯,০০০ টাকা পাঠাচ্ছেন। ওয়ালেটে এটি দেখাল:",
    en: "Another case. Yesterday you got a new phone and reset your PIN. Tonight at 11 pm you send Tk 9,000. The wallet shows:",
  },
  t2q1: { bn: "এরপর কী হবে?", en: "What happens next?" },
  task3: { bn: "কাজ ৩ · বিশ্লেষকের কাজ", en: "Task 3 · The analyst" },
  task3Intro: {
    bn: "শেষ কাজ: ধরুন আপনি একটি মোবাইল ব্যাংকিং প্রতিষ্ঠানের প্রতারণা-বিশ্লেষক। আজ সকালের ১২টি প্রতারণা-সতর্কতা দেখে দুটি প্রশ্নের উত্তর দেবেন। আমরা সময় মাপব, তবে তাড়াহুড়ো করবেন না।",
    en: "Last task: imagine you are a fraud analyst at a mobile-money company. You will look at 12 scam alerts from this morning and answer two questions. We measure the time, but do not rush.",
  },
  start: { bn: "শুরু করি", en: "Start" },
  ringsQ: { bn: "এই সতর্কতাগুলোতে কয়টি আলাদা প্রতারণা-চক্র আছে?", en: "How many separate scam rings are in these alerts?" },
  ringsHint: {
    bn: "চক্র = ২ বা তার বেশি সতর্কতা, যাদের টাকা শেষে একই ওয়ালেটে যায়।",
    en: "A ring = 2 or more alerts whose money ends up in the same wallet.",
  },
  walletQ: { bn: "দল কোন ওয়ালেটটি আগে যাচাই করবে? (যেটিতে সবচেয়ে বেশি ভুক্তভোগী)", en: "Which wallet should the team check first? (the one with the most victims)" },
  submitAnswers: { bn: "উত্তর জমা দিন", en: "Submit answers" },
  commentQ: { bn: "কিছু কি অস্পষ্ট লেগেছে, বা ভালো লেগেছে?", en: "Was anything confusing, or anything you liked?" },
  commentHint: { bn: "ঐচ্ছিক। নাম বা ফোন নম্বর লিখবেন না।", en: "Optional. Please do not write your name or phone number." },
  finish: { bn: "শেষ করি", en: "Finish" },
  skip: { bn: "বাদ দিন", en: "Skip" },
  thanks: { bn: "ধন্যবাদ!", en: "Thank you!" },
  saved: { bn: "আপনার উত্তর নাম ছাড়া সংরক্ষিত হয়েছে।", en: "Your answers are saved, without your name." },
  savedOffline: { bn: "ইন্টারনেট নেই, তাই উত্তর এই ফোনে রাখা হয়েছে। পরে নিজে থেকে পাঠানো হবে।", en: "No connection, so the answers are kept on this phone and sent automatically later." },
  saving: { bn: "সংরক্ষণ করা হচ্ছে…", en: "Saving…" },
  debrief: {
    bn: "মনে রাখবেন: আসল পুরস্কারের জন্য কখনো ফি দিতে হয় না। সন্দেহ হলে টাকা পাঠানোর আগে থামুন এবং জানা নম্বরে ফোন করে যাচাই করুন।",
    en: "Remember: a real prize never asks for a fee. If in doubt, pause before sending and check on a number you already know.",
  },
  nextParticipant: { bn: "পরবর্তী অংশগ্রহণকারী", en: "Next participant" },
  pending: { bn: "অফলাইনে সংরক্ষিত", en: "Saved offline" },
  waiting: { bn: "বাকি", en: "pending" },
} satisfies Record<string, Bi | Bi[]>;

type Answers = {
  profile: StudyPayload["profile"];
  q1?: string;
  q2?: string;
  q3?: string;
  q4?: number;
  q5?: number;
  q6?: number;
  t2q1?: string;
  t2q2?: number;
  rings?: number;
  wallet?: string;
  confidence?: number;
  comment: string;
};

type Participant = {
  clientId: string;
  arm: "A" | "B";
  screenLang: L;
  meaningOptions: Option[];
  nextOptions: Option[];
  startedAt: string;
};

function newParticipant(): Participant {
  const { arm, screenLang } = nextAssignment();
  return {
    clientId: newId(),
    arm,
    screenLang,
    meaningOptions: [...shuffle(T1_MEANING), NOT_SURE],
    nextOptions: [...shuffle(T2_NEXT), NOT_SURE],
    startedAt: new Date().toISOString(),
  };
}

const usePending = () =>
  useSyncExternalStore(
    onQueueChange,
    () => pendingResponses().length,
    () => 0,
  );

export function StudyFlow() {
  const [lang, setLang] = useState<L>("bn");
  const [step, setStep] = useState<Step>("consent");
  const [p, setP] = useState<Participant>(newParticipant);
  const [a, setA] = useState<Answers>({ profile: {}, comment: "" });
  const [fac, setFac] = useState(getFacilitator);
  const [showMock, setShowMock] = useState(false);
  const [sync, setSync] = useState<"idle" | "saving" | "sent" | "queued">("idle");
  const [menu, setMenu] = useState(false);
  const taps = useRef<number[]>([]);
  const at = useRef<Record<string, number>>({});
  const pending = usePending();

  // Upload anything left from earlier participants: now, every 30 s and whenever the phone comes back online.
  useEffect(() => {
    flushQueue();
    const id = setInterval(flushQueue, 30000);
    window.addEventListener("online", flushQueue);
    const params = new URLSearchParams(window.location.search);
    if (params.get("facilitator") === "1") setTimeout(() => setMenu(true), 0);
    return () => {
      clearInterval(id);
      window.removeEventListener("online", flushQueue);
    };
  }, []);

  const go = useCallback((s: Step) => {
    at.current[s] ??= performance.now(); // first time this screen opened
    setShowMock(false);
    setStep(s);
    window.scrollTo({ top: 0 });
  }, []);

  const idx = STEPS.indexOf(step);
  const back = () => idx > 0 && step !== "done" && go(STEPS[idx - 1]);
  const advance = () => go(STEPS[Math.min(STEPS.length - 1, idx + 1)]);
  const choose = (patch: Partial<Answers>) => {
    setA((x) => ({ ...x, ...patch }));
    setTimeout(advance, 220);
  };
  const ms = (from: string, to: string) => {
    const x = at.current[from];
    const y = at.current[to];
    return x != null && y != null ? Math.max(0, Math.round(y - x)) : undefined;
  };

  const finish = async (comment: string | null) => {
    at.current.end = performance.now();
    const payload: StudyPayload = {
      study_version: STUDY_VERSION,
      client_id: p.clientId,
      consent: true,
      facilitator: fac.trim().toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 8) || null,
      ui_lang: lang,
      assignment: `${p.arm}-${p.screenLang}`,
      started_at: p.startedAt,
      total_ms: ms("p_age_band", "end"),
      profile: a.profile,
      task1: {
        lang: p.screenLang,
        q1_meaning: a.q1,
        q2_action: a.q2,
        q3_reason: a.q3,
        q4_clarity: a.q4,
        q5_trust: a.q5,
        q6_annoyance: a.q6,
        view_ms: ms("t1_view", "t1_q1"),
        total_ms: ms("t1_view", "t2_view"),
      },
      task2: { lang: p.screenLang, q_next: a.t2q1, q_ok_unsure: a.t2q2, view_ms: ms("t2_view", "t2_q1"), total_ms: ms("t2_view", "t3_intro") },
      task3: { arm: p.arm, rings: a.rings, first_wallet: a.wallet, time_ms: ms("t3_task", "t3_conf"), confidence: a.confidence },
      comment: comment?.trim() ? comment.trim().slice(0, 600) : null,
    };
    setSync("saving");
    go("done");
    setSync(await submitResponse(payload));
  };

  const reset = () => {
    setP(newParticipant());
    setA({ profile: {}, comment: "" });
    setSync("idle");
    setLang("bn");
    at.current = {};
    go("consent");
    flushQueue();
  };

  const tapVersion = () => {
    const now = Date.now();
    taps.current = [...taps.current.filter((t) => now - t < 2500), now];
    if (taps.current.length >= 5) {
      taps.current = [];
      setMenu(true);
    }
  };

  const tx = (b: Bi) => b[lang];
  const progress = idx / (STEPS.length - 1);

  let body: ReactNode = null;
  const profileQ = PROFILE.find((q) => `p_${q.key}` === step);
  if (step === "consent") {
    body = (
      <div className="space-y-6">
        <div>
          <p className="label-mono">UVERA · {tx(T.study)}</p>
          <h1 className="mt-3 text-[1.7rem] font-semibold leading-tight tracking-tight">{tx(T.consentTitle)}</h1>
          <p className="mt-3 text-muted-foreground">{tx(T.consentLead)}</p>
        </div>
        <ul className="space-y-3">
          {T.consent.map((c, i) => (
            <li key={i} className="flex gap-3">
              <ShieldCheck className="mt-1 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span>{tx(c)}</span>
            </li>
          ))}
        </ul>
        <label className="block space-y-1.5">
          <span className="block text-sm text-muted-foreground">{tx(T.facilitator)}</span>
          <input
            value={fac}
            onChange={(e) => {
              const v = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 8);
              setFac(v);
              setFacilitator(v);
            }}
            placeholder="F1"
            autoComplete="off"
            className="h-12 w-28 rounded-xl border border-border bg-background px-3 font-mono text-lg uppercase"
          />
        </label>
        <Primary onClick={() => go("p_age_band")}>{tx(T.agree)}</Primary>
      </div>
    );
  } else if (profileQ) {
    body = (
      <Question kicker={tx(T.aboutYou)} q={tx(profileQ.q)}>
        <Choices
          options={profileQ.options}
          value={a.profile[profileQ.key]}
          lang={lang}
          onPick={(v) => choose({ profile: { ...a.profile, [profileQ.key]: v } })}
        />
      </Question>
    );
  } else if (step === "t1_view") {
    body = (
      <div className="space-y-5">
        <p className="label-mono">{tx(T.task1)}</p>
        <p className="text-lg">{tx(T.task1Context)}</p>
        <div className="rounded-2xl rounded-tl-sm border border-border bg-muted/60 p-4 text-[15px]">
          <p className="mb-1 font-mono text-[11px] text-faint">SMS · 01XXXXXXXXX</p>
          {tx(T.sms)}
        </div>
        <p className="text-lg">{tx(T.task1Then)}</p>
        <PauseMock lang={p.screenLang} />
        <Primary onClick={advance}>{tx(T.readIt)}</Primary>
      </div>
    );
  } else if (step.startsWith("t1_q")) {
    const n = Number(step.slice(4));
    const mock = <MockToggle open={showMock} setOpen={setShowMock} lang={lang} mock={<PauseMock lang={p.screenLang} />} />;
    if (n === 1)
      body = (
        <Question kicker={tx(T.task1)} q={tx(T.q1)} extra={mock}>
          <Choices options={p.meaningOptions} value={a.q1} lang={lang} onPick={(v) => choose({ q1: v })} />
        </Question>
      );
    if (n === 2)
      body = (
        <Question kicker={tx(T.task1)} q={tx(T.q2)} extra={mock}>
          <Choices options={T1_ACTION} value={a.q2} lang={lang} onPick={(v) => choose({ q2: v })} />
        </Question>
      );
    if (n === 3)
      body = (
        <Question kicker={tx(T.task1)} q={tx(T.q3)} extra={mock}>
          <Choices options={T1_REASON} value={a.q3} lang={lang} onPick={(v) => choose({ q3: v })} />
        </Question>
      );
    if (n === 4) body = <ScaleScreen kicker={tx(T.task1)} s={SCALES.clarity} lang={lang} value={a.q4} extra={mock} onPick={(v) => choose({ q4: v })} />;
    if (n === 5) body = <ScaleScreen kicker={tx(T.task1)} s={SCALES.trust} lang={lang} value={a.q5} extra={mock} onPick={(v) => choose({ q5: v })} />;
    if (n === 6) body = <ScaleScreen kicker={tx(T.task1)} s={SCALES.annoyance} lang={lang} value={a.q6} extra={mock} onPick={(v) => choose({ q6: v })} />;
  } else if (step === "t2_view") {
    body = (
      <div className="space-y-5">
        <p className="label-mono">{tx(T.task2)}</p>
        <p className="text-lg">{tx(T.task2Context)}</p>
        <UnsureMock lang={p.screenLang} />
        <Primary onClick={advance}>{tx(T.readIt)}</Primary>
      </div>
    );
  } else if (step === "t2_q1" || step === "t2_q2") {
    const mock = <MockToggle open={showMock} setOpen={setShowMock} lang={lang} mock={<UnsureMock lang={p.screenLang} />} />;
    body =
      step === "t2_q1" ? (
        <Question kicker={tx(T.task2)} q={tx(T.t2q1)} extra={mock}>
          <Choices options={p.nextOptions} value={a.t2q1} lang={lang} onPick={(v) => choose({ t2q1: v })} />
        </Question>
      ) : (
        <ScaleScreen kicker={tx(T.task2)} s={SCALES.okUnsure} lang={lang} value={a.t2q2} extra={mock} onPick={(v) => choose({ t2q2: v })} />
      );
  } else if (step === "t3_intro") {
    body = (
      <div className="space-y-6">
        <p className="label-mono">{tx(T.task3)}</p>
        <p className="text-lg">{tx(T.task3Intro)}</p>
        <Primary onClick={advance}>{tx(T.start)}</Primary>
      </div>
    );
  } else if (step === "t3_task") {
    const ready = a.rings != null && !!a.wallet;
    body = (
      <div className="space-y-6">
        <p className="label-mono">
          {tx(T.task3)} · {p.arm === "A" ? (lang === "bn" ? "সতর্কতার তালিকা" : "Alert list") : lang === "bn" ? "যুক্ত কেস" : "Linked cases"}
        </p>
        {p.arm === "A" ? <TriageList lang={lang} /> : <TriageCases lang={lang} />}
        <div className="space-y-3 rounded-2xl border border-border p-4">
          <p className="text-lg font-medium leading-snug">{tx(T.ringsQ)}</p>
          <p className="text-sm text-muted-foreground">{tx(T.ringsHint)}</p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="minus"
              onClick={() => setA((x) => ({ ...x, rings: Math.max(0, (x.rings ?? 1) - 1) }))}
              className="grid size-14 place-items-center rounded-2xl border border-border active:bg-muted"
            >
              <Minus className="size-5" />
            </button>
            <span className="num w-16 text-center font-mono text-4xl font-semibold" aria-live="polite">
              {a.rings ?? "?"}
            </span>
            <button
              type="button"
              aria-label="plus"
              onClick={() => setA((x) => ({ ...x, rings: Math.min(12, (x.rings ?? -1) + 1) }))}
              className="grid size-14 place-items-center rounded-2xl border border-border active:bg-muted"
            >
              <Plus className="size-5" />
            </button>
          </div>
        </div>
        <div className="space-y-3 rounded-2xl border border-border p-4">
          <p className="text-lg font-medium leading-snug">{tx(T.walletQ)}</p>
          <div className="grid grid-cols-2 gap-2">
            {WALLET_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setA((x) => ({ ...x, wallet: o.value }))}
                aria-pressed={a.wallet === o.value}
                className={cn(
                  "min-h-14 rounded-2xl border px-3 text-base transition-colors",
                  o.value === "not_sure" ? "col-span-2" : "font-mono",
                  a.wallet === o.value ? "border-foreground bg-foreground text-background" : "border-border active:bg-muted",
                )}
              >
                {o.label[lang]}
              </button>
            ))}
          </div>
        </div>
        <Primary onClick={advance} disabled={!ready}>
          {tx(T.submitAnswers)}
        </Primary>
      </div>
    );
  } else if (step === "t3_conf") {
    body = <ScaleScreen kicker={tx(T.task3)} s={SCALES.confidence} lang={lang} value={a.confidence} onPick={(v) => choose({ confidence: v })} />;
  } else if (step === "comment") {
    body = (
      <Question q={tx(T.commentQ)}>
        <p className="-mt-2 text-sm text-muted-foreground">{tx(T.commentHint)}</p>
        <textarea
          value={a.comment}
          onChange={(e) => setA((x) => ({ ...x, comment: e.target.value }))}
          rows={4}
          maxLength={500}
          className="w-full rounded-2xl border border-border bg-background p-3 text-base"
        />
        <Primary onClick={() => finish(a.comment)}>{tx(T.finish)}</Primary>
        <button type="button" onClick={() => finish(null)} className="w-full py-3 text-sm text-muted-foreground underline underline-offset-4">
          {tx(T.skip)}
        </button>
      </Question>
    );
  } else if (step === "done") {
    body = (
      <div className="flex min-h-[60svh] flex-col items-center justify-center gap-5 text-center">
        <Mark className="size-16" />
        <h1 className="text-3xl font-semibold tracking-tight">{tx(T.thanks)}</h1>
        <p className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          {sync === "saving" && tx(T.saving)}
          {sync === "sent" && (
            <>
              <CheckCircle2 className="size-4 text-safe" /> {tx(T.saved)}
            </>
          )}
          {sync === "queued" && (
            <>
              <CloudOff className="size-4 shrink-0" /> {tx(T.savedOffline)}
            </>
          )}
        </p>
        <p className="max-w-sm rounded-2xl border border-border p-4 text-left">{tx(T.debrief)}</p>
        <Primary onClick={reset} disabled={sync === "saving"}>
          {tx(T.nextParticipant)}
        </Primary>
      </div>
    );
  }

  return (
    <div
      className={cn("mx-auto flex min-h-svh max-w-[560px] flex-col", lang === "bn" && "bn [&_.label-mono]:font-bangla [&_.label-mono]:text-xs [&_.label-mono]:tracking-normal")}
      lang={lang}
    >
      <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur">
        <div className="flex h-14 items-center gap-3 px-4">
          {idx > 0 && step !== "done" ? (
            <button type="button" onClick={back} aria-label={tx(T.back)} className="-ml-2 grid size-10 place-items-center rounded-full text-muted-foreground active:bg-muted">
              <ChevronLeft className="size-5" />
            </button>
          ) : (
            <Mark className="size-6" />
          )}
          <span className="font-sans text-sm font-semibold tracking-[-0.02em]">UVERA</span>
          {pending > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-caution/60 px-2 py-0.5 font-mono text-[10px] text-caution">
              <CloudOff className="size-3" /> {tx(T.pending)} ({pending} {tx(T.waiting)})
            </span>
          )}
          <div className="ml-auto flex rounded-full border border-border p-0.5 text-xs" role="group" aria-label="Language">
            {(["bn", "en"] as const).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLang(l)}
                aria-pressed={lang === l}
                className={cn("h-8 rounded-full px-3", lang === l ? "bg-foreground text-background" : "text-muted-foreground", l === "bn" && "bn")}
              >
                {l === "bn" ? "বাংলা" : "English"}
              </button>
            ))}
          </div>
        </div>
        <div className="h-0.5 bg-muted" aria-hidden="true">
          <div className="h-full bg-foreground transition-[width] duration-300" style={{ width: `${progress * 100}%` }} />
        </div>
      </header>

      <main id="main" className="flex-1 px-4 pb-10 pt-6">
        {body}
      </main>

      <footer className="px-4 pb-6 text-center">
        <button type="button" onClick={tapVersion} className="label-mono select-none">
          {tx(T.of)} {Math.min(idx + 1, STEPS.length - 1)}/{STEPS.length - 1} · {STUDY_VERSION}
        </button>
      </footer>

      {menu && <FacilitatorMenu fac={fac} onClose={() => setMenu(false)} />}
    </div>
  );
}

function Primary({ children, onClick, disabled }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="h-14 w-full rounded-full bg-foreground text-lg font-medium text-background transition-opacity active:opacity-80 disabled:opacity-30"
    >
      {children}
    </button>
  );
}

function Question({ kicker, q, extra, children }: { kicker?: string; q: string; extra?: ReactNode; children: ReactNode }) {
  return (
    <div className="space-y-5">
      {kicker && <p className="label-mono">{kicker}</p>}
      {extra}
      <h1 className="text-[1.45rem] font-semibold leading-snug tracking-tight">{q}</h1>
      {children}
    </div>
  );
}

function Choices({ options, value, lang, onPick }: { options: Option[]; value?: string; lang: L; onPick: (v: string) => void }) {
  return (
    <div className="space-y-2.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onPick(o.value)}
          aria-pressed={value === o.value}
          className={cn(
            "flex min-h-14 w-full items-center rounded-2xl border px-4 py-3 text-left text-base leading-snug transition-colors",
            value === o.value ? "border-foreground bg-foreground text-background" : "border-border active:bg-muted",
          )}
        >
          {o.label[lang]}
        </button>
      ))}
    </div>
  );
}

function ScaleScreen({ kicker, s, lang, value, extra, onPick }: { kicker: string; s: ScaleQ; lang: L; value?: number; extra?: ReactNode; onPick: (v: number) => void }) {
  return (
    <Question kicker={kicker} q={s.q[lang]} extra={extra}>
      <div className="grid grid-cols-5 gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onPick(n)}
            aria-pressed={value === n}
            aria-label={`${n}${n === 1 ? ` (${s.low[lang]})` : n === 5 ? ` (${s.high[lang]})` : ""}`}
            className={cn(
              "num h-16 rounded-2xl border font-mono text-2xl font-semibold transition-colors",
              value === n ? "border-foreground bg-foreground text-background" : "border-border active:bg-muted",
            )}
          >
            {lang === "bn" ? "০১২৩৪৫"[n] : n}
          </button>
        ))}
      </div>
      <div className="flex justify-between gap-4 text-sm text-muted-foreground">
        <span>1 = {s.low[lang]}</span>
        <span className="text-right">5 = {s.high[lang]}</span>
      </div>
    </Question>
  );
}

function MockToggle({ open, setOpen, lang, mock }: { open: boolean; setOpen: (v: boolean) => void; lang: L; mock: ReactNode }) {
  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex h-10 items-center gap-2 rounded-full border border-border px-4 text-sm text-muted-foreground active:bg-muted"
      >
        {open ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        {open ? T.hide[lang] : T.showAgain[lang]}
      </button>
      {open && mock}
    </div>
  );
}

function FacilitatorMenu({ fac, onClose }: { fac: string; onClose: () => void }) {
  const pending = usePending();
  const [msg, setMsg] = useState("");
  const exportJson = () => {
    const blob = new Blob([JSON.stringify(pendingResponses(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `uvera-study-pending-${fac || "device"}-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "")}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <div className="fixed inset-0 z-50 grid place-items-end bg-black/60 sm:place-items-center" role="dialog" aria-modal="true" aria-label="Facilitator menu">
      <div className="w-full max-w-[560px] space-y-4 rounded-t-3xl border border-border bg-card p-5 font-sans sm:rounded-3xl" lang="en">
        <div className="flex items-center justify-between">
          <p className="font-semibold">Facilitator menu</p>
          <button type="button" onClick={onClose} className="h-9 rounded-full border border-border px-4 text-sm">
            Close
          </button>
        </div>
        <p className="text-sm text-muted-foreground">
          Device code <span className="font-mono text-foreground">{fac || "—"}</span> · <span className="font-mono text-foreground">{pending}</span> response(s) waiting to upload
        </p>
        <div className="grid gap-2">
          <button
            type="button"
            className="h-12 rounded-full bg-foreground font-medium text-background"
            onClick={async () => {
              setMsg("Uploading…");
              const left = await flushQueue();
              setMsg(left ? `${left} still waiting: the API is not reachable.` : "All uploaded.");
            }}
          >
            Upload now
          </button>
          <button type="button" className="h-12 rounded-full border border-border font-medium disabled:opacity-40" onClick={exportJson} disabled={!pending}>
            Export waiting responses (JSON)
          </button>
          <button
            type="button"
            className="h-12 rounded-full border border-border text-sm text-muted-foreground disabled:opacity-40"
            disabled={!pending}
            onClick={() => {
              if (window.confirm("Delete the waiting responses from this phone? Export them first.")) clearQueue();
            }}
          >
            Delete waiting responses from this phone
          </button>
          <Link href="/study/results" className="grid h-12 place-items-center rounded-full border border-border text-sm">
            Open live results (PIN)
          </Link>
        </div>
        {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
        <p className="text-xs text-faint">Open with 5 quick taps on the step counter, or /study?facilitator=1.</p>
      </div>
    </div>
  );
}
