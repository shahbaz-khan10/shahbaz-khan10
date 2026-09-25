import { cookies } from "next/headers";

export const API_BASE = process.env.API_BASE_URL || "http://127.0.0.1:8000/api";

export const ACCESS_COOKIE = "fct_am";
export const REFRESH_COOKIE = "fct_rm";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
}

export function readTokens(): Tokens {
  const store = cookies();
  return {
    access_token: store.get(ACCESS_COOKIE)?.value || "",
    refresh_token: store.get(REFRESH_COOKIE)?.value || "",
  };
}

export function persistTokens(access: string, refresh: string) {
  try {
    const store = cookies();
    store.set(ACCESS_COOKIE, access, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 });
    store.set(REFRESH_COOKIE, refresh, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 7 });
  } catch {
    // cookie writes are only allowed inside Server Actions / Route Handlers
  }
}

export function clearTokens() {
  try {
    const store = cookies();
    store.delete(ACCESS_COOKIE);
    store.delete(REFRESH_COOKIE);
  } catch {
    // ignore in read-only contexts
  }
}

export interface ApiOpts {
  method?: string;
  body?: unknown;
}

async function fetchJson(path: string, opts: ApiOpts, token: string): Promise<Response> {
  return fetch(API_BASE + path, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });
}

export async function api<T = unknown>(path: string, opts: ApiOpts = {}): Promise<T> {
  const tokens = readTokens();
  let res = await fetchJson(path, opts, tokens.access_token);

  if (res.status === 401 && tokens.refresh_token) {
    const rr = await fetch(API_BASE + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      cache: "no-store",
    });
    if (rr.ok) {
      const rd = (await rr.json()) as Tokens;
      persistTokens(rd.access_token, rd.refresh_token);
      res = await fetchJson(path, opts, rd.access_token);
    }
  }

  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j === "string" ? j : j.detail || msg;
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, String(msg));
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

export interface Paginated<T> {
  items: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}