"use client";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000").replace(/\/$/, "");

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

export async function post<T>(path: string, role: Role, body: unknown, subject?: string): Promise<T> {
  return api<T>(path, role, { method: "POST", body: JSON.stringify(body) }, subject);
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

/** Call the API as a demo persona. `subject` picks a different synthetic customer/agent than the default persona. */
export async function api<T>(path: string, role: Role, init: RequestInit = {}, subject?: string): Promise<T> {
  const key = tokenKey(role, subject);
  let token = memoryTokens[key] || readToken(key) || (await login(role, subject)).token;
  let res = await raw(path, init, token);
  if (res.status === 401) {
    token = (await login(role, subject)).token;
    res = await raw(path, init, token);
  }
  return parse<T>(res);
}

export async function publicGet<T>(path: string): Promise<T> {
  return parse<T>(await raw(path));
}
