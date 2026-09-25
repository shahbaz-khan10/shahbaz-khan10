import { cache } from "react";

import { api, ApiError } from "./core";
import type { UserPayload } from "./types";

export const getUser = cache(async (): Promise<UserPayload | null> => {
  try {
    return await api<UserPayload>("/auth/me");
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
});