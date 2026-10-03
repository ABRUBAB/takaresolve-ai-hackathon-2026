"use client";

import { createContext, useCallback, useContext, useEffect, useSyncExternalStore, type ReactNode } from "react";

export type Lang = "en" | "bn";

const DICT = {
  send_money: { en: "Send money", bn: "টাকা পাঠান" },
  check_sms: { en: "Check a message", bn: "বার্তা যাচাই" },
  guardian: { en: "Cash-flow", bn: "টাকার হিসাব" },
  home: { en: "Home", bn: "হোম" },
  balance: { en: "Balance", bn: "ব্যালেন্স" },
  recent: { en: "Recent activity", bn: "সাম্প্রতিক লেনদেন" },
  receiver: { en: "Receiver wallet", bn: "প্রাপকের ওয়ালেট" },
  amount: { en: "Amount (Tk)", bn: "পরিমাণ (টাকা)" },
  note: { en: "Message you received (optional)", bn: "আপনার পাওয়া বার্তা (ঐচ্ছিক)" },
  continue: { en: "Continue", bn: "এগিয়ে যান" },
  checking: { en: "Checking before you send…", bn: "পাঠানোর আগে যাচাই করা হচ্ছে…" },
  paused: { en: "Paused for your safety", bn: "আপনার নিরাপত্তার জন্য থামানো হয়েছে" },
  why: { en: "Why am I seeing this?", bn: "কেন এটি দেখছি?" },
  wait: { en: "Wait 10 minutes", bn: "১০ মিনিট অপেক্ষা করুন" },
  verify: { en: "Verify the number", bn: "নম্বরটি যাচাই করুন" },
  ask: { en: "Ask someone I trust", bn: "বিশ্বস্ত কাউকে জিজ্ঞেস করুন" },
  send_anyway: { en: "I'm sure, send anyway", bn: "আমি নিশ্চিত, পাঠাব" },
  send_now: { en: "Send now", bn: "এখন পাঠান" },
  not_sure: { en: "Not sure — a person will check", bn: "নিশ্চিত নয় — একজন কর্মী যাচাই করবেন" },
  never_blocked: { en: "You are never blocked. You decide.", bn: "আপনাকে কখনো আটকানো হবে না। সিদ্ধান্ত আপনার।" },
  hello: { en: "Good evening", bn: "শুভ সন্ধ্যা" },
  available: { en: "Available balance", bn: "ব্যবহারযোগ্য ব্যালেন্স" },
  looks_fine: { en: "Looks fine", bn: "ঠিক আছে বলে মনে হচ্ছে" },
  some_signs: { en: "Some warning signs", bn: "কিছু সতর্ক সংকেত আছে" },
  sent: { en: "Sent", bn: "পাঠানো হয়েছে" },
  demo_no_money: { en: "Demo only: no real money moves.", bn: "শুধু ডেমো: কোনো আসল টাকা যায় না।" },
  check_message: { en: "Check this message", bn: "বার্তাটি যাচাই করুন" },
  paste_here: { en: "Paste the SMS you received", bn: "আপনার পাওয়া এসএমএস এখানে দিন" },
  likely_scam: { en: "Likely a scam", bn: "সম্ভবত প্রতারণা" },
  likely_safe: { en: "Looks like a normal message", bn: "সাধারণ বার্তার মতো" },
  unsure_text: { en: "Not sure — be careful", bn: "নিশ্চিত নয় — সাবধান থাকুন" },
  next_7_days: { en: "Next 7 days", bn: "আগামী ৭ দিন" },
  low_balance_risk: { en: "Chance your balance falls below the safety floor", bn: "ব্যালেন্স নিরাপদ সীমার নিচে নামার সম্ভাবনা" },
  savings_goal: { en: "Savings goal", bn: "সঞ্চয়ের লক্ষ্য" },
  back: { en: "Back", bn: "ফিরে যান" },
  start_again: { en: "Start again", bn: "আবার শুরু করুন" },
  waiting: { en: "Waiting… take a breath.", bn: "অপেক্ষা করছি… একটু শান্ত হোন।" },
  call_official: { en: "Call the receiver on a number you already know, not one from the message.", bn: "বার্তার নম্বরে নয়, আপনার জানা নম্বরে প্রাপককে ফোন করুন।" },
} as const;

export type Key = keyof typeof DICT;

const KEY = "uvera.lang";
const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

function getSnapshot(): Lang {
  try {
    return localStorage.getItem(KEY) === "bn" ? "bn" : "en";
  } catch {
    return "en";
  }
}

const getServerSnapshot = (): Lang => "en";

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: Key) => string }>({
  lang: "en",
  setLang: () => {},
  t: (k) => DICT[k].en,
});

export function LangProvider({ children }: { children: ReactNode }) {
  const lang = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  useEffect(() => {
    document.documentElement.lang = lang; // screen readers pronounce Bangla correctly
  }, [lang]);
  const setLang = useCallback((l: Lang) => {
    try {
      localStorage.setItem(KEY, l);
    } catch {
      /* private mode: language resets on reload */
    }
    listeners.forEach((fn) => fn());
  }, []);
  return <Ctx.Provider value={{ lang, setLang, t: (k) => DICT[k][lang] }}>{children}</Ctx.Provider>;
}

export const useLang = () => useContext(Ctx);
