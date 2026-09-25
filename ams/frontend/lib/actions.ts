"use server";

import { redirect } from "next/navigation";

import { api, persistTokens, clearTokens, readTokens, ApiError } from "./core";

export interface ActionOutcome {
  error?: string;
  ok?: boolean;
}

export async function loginAction(formData: FormData): Promise<ActionOutcome> {
  const identifier = String(formData.get("identifier") || "").trim();
  const password = String(formData.get("password") || "");
  if (!identifier || !password) return { error: "Username and password are required." };

  try {
    const data = await api<any>("/auth/login", {
      method: "POST",
      body: { identifier, password },
    });
    persistTokens(data.access_token, data.refresh_token);
    return { ok: true };
  } catch (err) {
    return { error: err instanceof ApiError ? err.message : "Unable to reach the auth service." };
  }
}

export async function logoutAction() {
  const tokens = readTokens();
  try {
    if (tokens.refresh_token) {
      await api("/auth/logout", { method: "POST", body: { refresh_token: tokens.refresh_token } });
    }
  } catch {
    // best effort
  }
  clearTokens();
  redirect("/login");
}

export async function getRecord<T = Record<string, unknown>>(path: string, id: number): Promise<T | { error: string }> {
  try {
    return await api<T>(`${path}/${id}`);
  } catch (err) {
    return { error: err instanceof ApiError ? err.message : "Failed to load record." };
  }
}

export async function saveRecord(
  path: string,
  id: number | null,
  body: Record<string, unknown>,
): Promise<ActionOutcome> {
  try {
    const payload: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(body)) {
      if (v === "" || v === null || v === undefined) continue;
      payload[k] = v;
    }
    if (id) {
      await api(`${path}/${id}`, { method: "PATCH", body: payload });
    } else {
      await api(path, { method: "POST", body: payload });
    }
    return { ok: true };
  } catch (err) {
    return { error: err instanceof ApiError ? err.message : "Save failed." };
  }
}

export async function deleteRecord(path: string, id: number): Promise<ActionOutcome> {
  try {
    await api(`${path}/${id}`, { method: "DELETE" });
    return { ok: true };
  } catch (err) {
    return { error: err instanceof ApiError ? err.message : "Delete failed." };
  }
}

export async function setRolePermissions(roleId: number, permissionIds: number[]): Promise<ActionOutcome> {
  try {
    await api(`/roles/${roleId}/permissions`, { method: "PUT", body: { permission_ids: permissionIds } });
    return { ok: true };
  } catch (err) {
    return { error: err instanceof ApiError ? err.message : "Could not save permissions." };
  }
}