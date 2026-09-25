"use client";

import { useState } from "react";

import { setRolePermissions } from "@/lib/actions";

export interface PermCatalogItem {
  id: number;
  module: string;
  entity: string;
  action: string;
  codename: string;
}

export interface RoleBrief {
  id: number;
  name: string;
  permissionIds: number[];
  isSystem: boolean;
}

export default function PermsEditor({ roles, catalog }: { roles: RoleBrief[]; catalog: PermCatalogItem[] }) {
  const [roleId, setRoleId] = useState<number>(roles[0]?.id ?? 0);
  const [selected, setSelected] = useState<Set<number>>(new Set(roles[0]?.permissionIds ?? []));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const role = roles.find((r) => r.id === roleId);

  function switchRole(nextId: number) {
    setRoleId(nextId);
    setSelected(new Set(roles.find((r) => r.id === nextId)?.permissionIds ?? []));
    setMessage("");
  }

  function toggle(pid: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(pid)) next.delete(pid);
      else next.add(pid);
      return next;
    });
  }

  function toggleAll(pids: number[]) {
    setSelected((prev) => {
      const next = new Set(prev);
      const allOn = pids.every((p) => next.has(p));
      for (const p of pids) {
        if (allOn) next.delete(p);
        else next.add(p);
      }
      return next;
    });
  }

  async function save() {
    setMessage("");
    setSaving(true);
    const outcome = await setRolePermissions(roleId, Array.from(selected));
    setSaving(false);
    setMessage(outcome.ok ? "Permissions saved." : outcome.error || "Save failed.");
  }

  if (roles.length === 0) {
    return <p className="text-sm text-slate-500">No roles created yet.</p>;
  }

  const groups = new Map<string, PermCatalogItem[]>();
  for (const p of catalog) {
    const key = `${p.module} / ${p.entity}`;
    const arr = groups.get(key) || [];
    arr.push(p);
    groups.set(key, arr);
  }

  return (
    <div className="card mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Role permissions</h2>
          <select className="input w-56" value={roleId} onChange={(e) => switchRole(Number(e.target.value))}>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          {message ? <span className={`text-sm ${message === "Permissions saved." ? "text-green-600" : "text-red-600"}`}>{message}</span> : null}
          <button className="btn-primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      {role?.isSystem && role.name === "Super Admin" ? (
        <p className="px-4 py-3 text-sm text-amber-700">The Super Admin system role carries every permission - you cannot edit it.</p>
      ) : null}

      <div className="grid gap-x-6 gap-y-4 p-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from(groups.entries()).map(([label, perms]) => {
          const ids = perms.map((p) => p.id);
          const allOn = ids.every((i) => selected.has(i));
          return (
            <div key={label} className="rounded-md border border-slate-200 p-3">
              <button
                type="button"
                className="mb-2 flex w-full items-center justify-between text-left text-xs font-semibold uppercase tracking-wide text-slate-600 hover:text-brand-600"
                onClick={() => toggleAll(ids)}
              >
                <span>{label}</span>
                <span className={allOn ? "text-green-600" : ""}>{allOn ? "all ✓" : "+ all"}</span>
              </button>
              <div className="flex flex-wrap gap-1.5">
                {perms.map((p) => (
                  <label
                    key={p.id}
                    className={`cursor-pointer rounded-full border px-2.5 py-0.5 text-xs ${selected.has(p.id) ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-500"}`}
                  >
                    <input type="checkbox" className="hidden" checked={selected.has(p.id)} onChange={() => toggle(p.id)} />
                    {p.action}
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}