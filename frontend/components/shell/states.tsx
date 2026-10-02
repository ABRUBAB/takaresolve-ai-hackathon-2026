"use client";

import { Loader2, ServerCrash } from "lucide-react";
import { Mark } from "@/components/brand/logo";
import type { ApiError } from "@/lib/api";

export function Warming({ label = "Starting the AI engines…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
      <Mark className="size-10 animate-pulse" />
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="label-mono">The free server wakes up in about a minute</p>
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> {label}
    </div>
  );
}

export function ErrorBox({ error, retry }: { error: ApiError | null; retry?: () => void }) {
  if (!error) return null;
  const detail = typeof error.detail === "string" ? error.detail : (error.detail as { detail?: string })?.detail;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-border p-4 text-sm">
      <ServerCrash className="mt-0.5 size-4 text-muted-foreground" />
      <div className="space-y-1">
        <p className="font-medium">Could not load this</p>
        <p className="text-muted-foreground">
          {detail || (error.status === 0 ? "The API is not reachable. Is it running?" : `Error ${error.status}`)}
        </p>
        {retry && (
          <button onClick={retry} className="text-xs underline underline-offset-4">
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function Guard<T>({ q, children, warmingLabel }: {
  q: { data: T | null; error: ApiError | null; loading: boolean; warming: boolean; reload: () => void };
  children: (data: T) => React.ReactNode;
  warmingLabel?: string;
}) {
  if (q.warming) return <Warming label={warmingLabel} />;
  if (q.error) return <ErrorBox error={q.error} retry={q.reload} />;
  if (!q.data) return <Loading />;
  return <>{children(q.data)}</>;
}
