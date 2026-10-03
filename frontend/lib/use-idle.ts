"use client";

import { useEffect, useState } from "react";

/** True once the browser is idle after the first paint, so heavy WebGL work never delays the text people read first. */
export function useIdle(timeout = 1500) {
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    const w = window as Window & { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number; cancelIdleCallback?: (id: number) => void };
    if (w.requestIdleCallback) {
      const id = w.requestIdleCallback(() => setIdle(true), { timeout });
      return () => w.cancelIdleCallback?.(id);
    }
    const t = setTimeout(() => setIdle(true), 300);
    return () => clearTimeout(t);
  }, [timeout]);
  return idle;
}
