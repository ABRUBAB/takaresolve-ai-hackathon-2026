"use client";

import { useSyncExternalStore } from "react";

/**
 * API client. Two modes:
 *  - live: calls the FastAPI service at NEXT_PUBLIC_API_BASE (local dev defaults to http://127.0.0.1:8000);
 *  - recorded: plays back real responses recorded from that API for every demo scenario (public/data/snapshot.json,
 *    made by scripts/export_snapshot.py). Used when no API is configured, or as a fallback while the live API is
 *    offline or waking up, so the hosted demo always works.
 */
const RAW_BASE = process.env.NEXT_PUBLIC_API_BASE?.trim();
export const API_BASE = (RAW_BASE && RAW_BASE !== "snapshot" ? RAW_BASE : process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "").replace(/\/$/, "");
export const RECORDED_ONLY = !API_BASE;

export type Role = "customer" | "agent" | "ops";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API error ${status}`);
    this.status = status;
    this.detail = detail;
  }
  get warmingUp() {
    return this.status === 503;
  }
}

// ---------------------------------------------------------------- recorded responses

type Snapshot = { recorded_at: string; responses: Record<string, unknown> };
let snapshot: Promise<Snapshot | null> | null = null;

function loadSnapshot() {
  snapshot ??= fetch("/data/snapshot.json", { cache: "force-cache" })
    .then((r) => (r.ok ? (r.json() as Promise<Snapshot>) : null))
    .catch(() => null);
  return snapshot;
}

/** JSON with sorted keys and whole numbers written without ".0", matching scripts/export_snapshot.py. */
function stable(v: unknown): string {
  if (Array.isArray(v)) return `[${v.map(stable).join(",")}]`;
  if (v && typeof v === "object")
    return `{${Object.keys(v as Record<string, unknown>)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${stable((v as Record<string, unknown>)[k])}`)
      .join(",")}}`;
  return JSON.stringify(v);
}

const snapKey = (method: string, path: string, body?: unknown) => `${method} ${path}${body !== undefined ? ` ${stable(body)}` : ""}`;

let usedRecorded = false;
const listeners = new Set<() => void>();
function setRecorded(on: boolean) {
  if (usedRecorded === on) return;
  usedRecorded = on;
  listeners.forEach((fn) => fn());
}
const markRecorded = () => setRecorded(true);

/** True once any response on this page came from the recordings (shown as a badge in the top bar). */
export function useRecordedMode() {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => usedRecorded || RECORDED_ONLY,
    () => RECORDED_ONLY,
  );
}

const OFFLINE =
  "The live model is offline right now. This hosted demo plays back real recorded results for the preset examples — pick one of them.";

async function fromRecording<T>(method: string, path: string, body?: unknown): Promise<T | null> {
  const s = await loadSnapshot();
  if (!s) return null;
  const hit = s.responses[snapKey(method, path, body)];
  if (hit !== undefined) {
    markRecorded();
    return hit as T;
  }
  if (method === "POST" && /^\/cases\/[^/]+\/actions$/.test(path)) {
    markRecorded();
    return { message: "Recorded for this demo session only (the live API is offline, so nothing was saved)." } as T;
  }
  return null;
}

// ---------------------------------------------------------------- live calls

const tokenKey = (role: Role, subject?: string) => `uvera.token.${role}.${subject ?? "default"}`;

function readToken(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function saveToken(key: string, token: string) {
  try {
    sessionStorage.setItem(key, token);
  } catch {
    /* private mode: keep in memory only */
  }
}

const memoryTokens: Record<string, string> = {};

async function raw(path: string, init: RequestInit = {}, token?: string): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  try {
    return await fetch(`${API_BASE}/v1${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError(0, "The API is not reachable right now.");
  }
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? body);
  return body as T;
}

export async function login(role: Role, subjectId?: string): Promise<{ token: string; subject_id: string; display_name: string }> {
  const res = await raw("/auth/demo-login", { method: "POST", body: JSON.stringify({ role, subject_id: subjectId }) });
  const out = await parse<{ token: string; subject_id: string; display_name: string }>(res);
  const key = tokenKey(role, subjectId);
  memoryTokens[key] = out.token;
  saveToken(key, out.token);
  return out;
}

async function live<T>(path: string, role: Role | null, init: RequestInit, subject?: string): Promise<T> {
  if (!role) return parse<T>(await raw(path, init));
  const key = tokenKey(role, subject);
  let token = memoryTokens[key] || readToken(key) || (await login(role, subject)).token;
  let res = await raw(path, init, token);
  if (res.status === 401) {
    token = (await login(role, subject)).token;
    res = await raw(path, init, token);
  }
  return parse<T>(res);
}

async function call<T>(path: string, role: Role | null, init: RequestInit = {}, subject?: string): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const body = typeof init.body === "string" ? JSON.parse(init.body) : undefined;
  if (RECORDED_ONLY) {
    const hit = await fromRecording<T>(method, path, body);
    if (hit) return hit;
    throw new ApiError(404, OFFLINE);
  }
  try {
    const out = await live<T>(path, role, init, subject);
    setRecorded(false); // the live API answered: drop the "Recorded demo" badge
    return out;
  } catch (e) {
    const err = e instanceof ApiError ? e : new ApiError(0, String(e));
    // offline, waking up or rate-limited: answer from the recordings when this exact request was recorded
    if (err.status === 0 || err.status === 429 || err.status === 503 || err.status >= 500) {
      const hit = await fromRecording<T>(method, path, body);
      if (hit) return hit;
      if (err.status === 0) throw new ApiError(0, OFFLINE);
    }
    throw err;
  }
}

/** Call the API as a demo persona. `subject` picks a different synthetic customer/agent than the default persona. */
export async function api<T>(path: string, role: Role, init: RequestInit = {}, subject?: string): Promise<T> {
  return call<T>(path, role, init, subject);
}

export async function post<T>(path: string, role: Role, body: unknown, subject?: string): Promise<T> {
  return call<T>(path, role, { method: "POST", body: JSON.stringify(body) }, subject);
}

export async function publicGet<T>(path: string): Promise<T> {
  return call<T>(path, null);
}
