"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { loginAction } from "@/lib/actions";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string>("");
  const [pending, startTransition] = useTransition();

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setError("");
    startTransition(async () => {
      const outcome = await loginAction(formData);
      if (outcome.ok) {
        router.push("/");
        router.refresh();
      } else {
        setError(outcome.error || "Login failed.");
      }
    });
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-white">FCT Garments ERP</h1>
          <p className="mt-1 text-sm text-slate-400">Factory Administrator System</p>
        </div>
        <form onSubmit={onSubmit} className="card space-y-4 p-6">
          <div>
            <label htmlFor="identifier" className="label">
              Username or email
            </label>
            <input id="identifier" name="identifier" className="input" autoComplete="username" required autoFocus />
          </div>
          <div>
            <label htmlFor="password" className="label">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              className="input"
              autoComplete="current-password"
              required
            />
          </div>
          {error ? <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
          <button type="submit" disabled={pending} className="btn-primary w-full">
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}