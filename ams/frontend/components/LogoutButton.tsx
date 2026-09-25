"use client";

import { useTransition } from "react";

import { logoutAction } from "@/lib/actions";

export default function LogoutButton() {
  const [pending, startTransition] = useTransition();
  return (
    <button
      className="btn-secondary"
      disabled={pending}
      onClick={() => startTransition(() => logoutAction())}
    >
      Sign out
    </button>
  );
}