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

const tokenKey = (role: Role) => `uvera.token.${role}`;

function readToken(role: Role): string | null {
  try {
    return sessionStorage.getItem(tokenKey(role));
  } catch {
    return null;
  }
}

function saveToken(role: Role, token: string) {
  try {
    sessionStorage.setItem(tokenKey(role), token);
  } catch {
    /* private mode: keep in memory only */
  }
}

const memoryTokens: Partial<Record<Role, string>> = {};

async function raw(path: string, init: RequestInit = {}, token?: string): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_BASE}/v1${path}`, { ...init, headers, cache: "no-store" });
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
  memoryTokens[role] = out.token;
  saveToken(role, out.token);
  return out;
}

export async function api<T>(path: string, role: Role, init: RequestInit = {}): Promise<T> {
  let token = memoryTokens[role] || readToken(role) || (await login(role)).token;
  let res = await raw(path, init, token);
  if (res.status === 401) {
    token = (await login(role)).token;
    res = await raw(path, init, token);
  }
  return parse<T>(res);
}

export async function publicGet<T>(path: string): Promise<T> {
  return parse<T>(await raw(path));
}
