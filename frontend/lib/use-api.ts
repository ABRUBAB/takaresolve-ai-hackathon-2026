"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type Role } from "./api";

type State<T> = { data: T | null; error: ApiError | null; loading: boolean; warming: boolean };

/** Fetch an API path for a role. Retries automatically while the AI engines are warming up (HTTP 503). */
export function useApi<T>(path: string | null, role: Role) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: !!path, warming: false });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    if (!path) return;
    setState((s) => ({ ...s, loading: true }));
    try {
      const data = await api<T>(path, role);
      setState({ data, error: null, loading: false, warming: false });
    } catch (e) {
      const err = e instanceof ApiError ? e : new ApiError(0, String(e));
      if (err.warmingUp) {
        setState((s) => ({ ...s, warming: true, loading: true, error: err }));
        timer.current = setTimeout(load, 3000);
      } else {
        setState({ data: null, error: err, loading: false, warming: false });
      }
    }
  }, [path, role]);

  useEffect(() => {
    load();
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [load]);

  return { ...state, reload: load };
}
