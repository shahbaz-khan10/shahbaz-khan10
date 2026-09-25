"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { MENU, can } from "@/lib/menus";
import type { UserPayload } from "@/lib/types";

export default function Sidebar({ user }: { user: UserPayload }) {
  const pathname = usePathname();
  const items = MENU.filter((m) => can(user.perms, m.perm));

  return (
    <aside className="flex w-60 shrink-0 flex-col bg-slate-900 text-slate-300">
      <div className="border-b border-slate-800 px-4 py-4">
        <p className="text-sm font-bold text-white">FCT Garments ERP</p>
        <p className="text-xs text-slate-500">Phase 1 - AMS</p>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {items.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 px-4 py-2 text-sm ${active ? "bg-brand-700 text-white" : "hover:bg-slate-800"}`}
            >
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-800 px-4 py-3">
        <p className="truncate text-sm font-medium text-white">{user.full_name}</p>
        <p className="truncate text-xs text-slate-500">{user.username}</p>
        <p className="mt-1 truncate text-xs text-brand-300">{user.roles.join(", ")}</p>
      </div>
    </aside>
  );
}