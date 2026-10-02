"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Role } from "./api";

type State<T> = { data: T | null; error: ApiError | null; loading: boolean; warming: boolean };

/** Fetch an API path for a role. Retries automatically while the AI engines are warming up (HTTP 503). */
export function useApi<T>(path: string | null, role: Role) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: !!path, warming: false });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function run(target: string) {
      try {
        const data = await api<T>(target, role);
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
  }, [path, role, nonce]);

  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    setNonce((n) => n + 1);
  }, []);

  return { ...state, reload };
}
