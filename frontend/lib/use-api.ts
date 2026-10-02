"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError, publicGet, type Role } from "./api";

type State<T> = { data: T | null; error: ApiError | null; loading: boolean; warming: boolean };

/** Fetch an API path for a role. Retries automatically while the AI engines are warming up (HTTP 503). */
export function useApi<T>(path: string | null, role: Role, subject?: string) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: !!path, warming: false });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function run(target: string) {
      try {
        const data = await api<T>(target, role, {}, subject);
        if (!cancelled) setState({ data, error: null, loading: false, warming: false });
      } catch (e) {
        if (cancelled) return;
        const err = e instanceof ApiError ? e : new ApiError(0, String(e));
        if (err.warmingUp) {
          setState((s) => ({ ...s, warming: true, loading: true, error: err }));
          timer = setTimeout(() => run(target), 3000);
        } else {
          setState({ data: null, error: err, loading: false, warming: false });
        }
      }
    }

    run(path);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [path, role, subject, nonce]);

  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    setNonce((n) => n + 1);
  }, []);

  return { ...state, reload };
}

/** Public (no login) GET with the same warming-up retry. */
export function usePublic<T>(path: string | null) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: !!path, warming: false });
  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function run(target: string) {
      try {
        const data = await publicGet<T>(target);
        if (!cancelled) setState({ data, error: null, loading: false, warming: false });
      } catch (e) {
        if (cancelled) return;
        const err = e instanceof ApiError ? e : new ApiError(0, String(e));
        if (err.warmingUp) {
          setState((s) => ({ ...s, warming: true, error: err }));
          timer = setTimeout(() => run(target), 3000);
        } else setState({ data: null, error: err, loading: false, warming: false });
      }
    }
    run(path);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [path]);
  return state;
}

type ActionState<T> = { data: T | null; error: ApiError | null; running: boolean; warming: boolean };

/** Run an API call on demand (button press). Waits and retries while the AI engines are warming up. */
export function useAction<T>() {
  const [state, setState] = useState<ActionState<T>>({ data: null, error: null, running: false, warming: false });
  const run = useCallback(async (call: () => Promise<T>): Promise<T | null> => {
    setState({ data: null, error: null, running: true, warming: false });
    for (let attempt = 0; attempt < 60; attempt++) {
      try {
        const data = await call();
        setState({ data, error: null, running: false, warming: false });
        return data;
      } catch (e) {
        const err = e instanceof ApiError ? e : new ApiError(0, String(e));
        if (!err.warmingUp) {
          setState({ data: null, error: err, running: false, warming: false });
          return null;
        }
        setState((s) => ({ ...s, warming: true }));
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
    setState({ data: null, error: new ApiError(503, "The AI engines are taking too long to start."), running: false, warming: false });
    return null;
  }, []);
  const reset = useCallback(() => setState({ data: null, error: null, running: false, warming: false }), []);
  return { ...state, run, reset };
}
