"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * One switch for all looping motion (WCAG 2.2.2 Pause, Stop, Hide). Respects the operating-system
 * "reduce motion" setting by default; the visitor can also pause or resume with the on-page button.
 */
const KEY = "uvera.motion";
const listeners = new Set<() => void>();
let memory: string | null = null;

function subscribe(cb: () => void) {
  listeners.add(cb);
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", cb);
  return () => {
    listeners.delete(cb);
    mq.removeEventListener("change", cb);
  };
}

function read(): string {
  let saved: string | null = memory;
  try {
    saved = localStorage.getItem(KEY) ?? memory;
  } catch {
    /* storage blocked: use the in-memory choice */
  }
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return `${reduced ? 1 : 0}${saved ?? "-"}`;
}

export function useMotionPref() {
  const snap = useSyncExternalStore(subscribe, read, () => "0-");
  const reduced = snap[0] === "1";
  const saved = snap.slice(1);
  const paused = saved === "paused" || (saved === "-" && reduced);
  const setPaused = useCallback((p: boolean) => {
    memory = p ? "paused" : "playing";
    try {
      localStorage.setItem(KEY, p ? "paused" : "playing");
    } catch {
      /* private mode: the choice lasts until reload */
    }
    listeners.forEach((fn) => fn());
  }, []);
  return { animate: !paused, paused, reduced, setPaused };
}
