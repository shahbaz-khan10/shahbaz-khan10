import Link from "next/link";
import { redirect } from "next/navigation";

import { api } from "@/lib/core";
import { MENU, can } from "@/lib/menus";
import { getUser } from "@/lib/user";

async function count(userPerms: string[], thing: string, pathEnd: string): Promise<number | null> {
  if (!can(userPerms, `ams.${thing}.view`)) return null;
  try {
    const d = await api<{ pagination: { total: number } }>(`${pathEnd}?page_size=1`);
    return d.pagination.total;
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const user = await getUser();
  if (!user) redirect("/login");

  const [departments, employees, users, roles, items, buyers] = await Promise.all([
    count(user.perms, "department", "/departments"),
    count(user.perms, "employee", "/employees"),
    count(user.perms, "user", "/users"),
    count(user.perms, "role", "/roles"),
    count(user.perms, "item", "/items"),
    count(user.perms, "buyer", "/buyers"),
  ]);

  const cards = [
    { label: "Departments", value: departments },
    { label: "Employees", value: employees },
    { label: "Items", value: items },
    { label: "Buyers", value: buyers },
    { label: "Users", value: users },
    { label: "Roles", value: roles },
  ];

  const modules = MENU.filter((m) => can(user.perms, m.perm));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Welcome back, {user.full_name}</h1>
        <p className="text-sm text-slate-500">{user.roles.join(", ") || "No roles assigned"}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        {cards.map((card) => (
          <div key={card.label} className="card p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{card.label}</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{card.value ?? "—"}</p>
          </div>
        ))}
      </div>

      <div className="card p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Modules</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
          {modules.map((m) => (
            <Link
              key={m.href}
              href={m.href}
              className="flex items-center gap-3 rounded-md border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 hover:border-brand-500 hover:bg-brand-50"
            >
              <span className="text-lg">{m.icon}</span>
              {m.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}