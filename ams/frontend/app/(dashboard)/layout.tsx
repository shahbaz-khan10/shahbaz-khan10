import { redirect } from "next/navigation";

import LogoutButton from "@/components/LogoutButton";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/core";
import type { UserPayload } from "@/lib/types";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  let user: UserPayload | null = null;
  try {
    user = await api<UserPayload>("/auth/me");
  } catch {
    user = null;
  }
  if (!user) redirect("/login");

  return (
    <div className="flex min-h-screen">
      <Sidebar user={user} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-end border-b border-slate-200 bg-white px-6 py-3">
          <LogoutButton />
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}