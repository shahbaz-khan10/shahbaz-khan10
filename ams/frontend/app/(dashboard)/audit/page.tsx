import { api, type Paginated } from "@/lib/core";
import { can } from "@/lib/menus";
import { getUser } from "@/lib/user";

interface AuditRow {
  id: number;
  action: string;
  action_label: string;
  actor_username: string | null;
  actor_label: string | null;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  ip_address: string | null;
  notes: string;
  created_at: string;
}

const ACTIONS = ["create", "update", "delete", "login", "logout", "password_change", "password_reset"];

export default async function AuditPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[]>;
}) {
  const user = await getUser();
  if (!user || !can(user.perms, "ams.audit.view")) {
    return (
      <div className="card p-10 text-center text-slate-500">
        You do not have the <code>ams.audit.view</code> permission.
      </div>
    );
  }

  const param = (key: string) => {
    const v = searchParams?.[key];
    return Array.isArray(v) ? v[0] ?? "" : v ?? "";
  };
  const q = param("q");
  const action = param("action");
  const entity = param("entity");
  const dateFrom = param("date_from");
  const dateTo = param("date_to");
  const page = Math.max(1, Number(param("page")) || 1);

  const query = new URLSearchParams({ page: String(page), page_size: "25" });
  if (q) query.set("q", q);
  if (action) query.set("action", action);
  if (entity) query.set("entity_type", entity);
  if (dateFrom) query.set("date_from", dateFrom);
  if (dateTo) query.set("date_to", dateTo);

  const data = await api<Paginated<AuditRow>>(`/audit/logs?${query.toString()}`);

  return (
    <div className="card">
      <div className="border-b border-slate-200 px-4 py-3">
        <h1 className="text-lg font-semibold text-slate-900">Audit Logs</h1>
        <p className="text-sm text-slate-500">Every create / update / delete and security event, attributed to its actor.</p>
      </div>
      <form method="get" className="grid grid-cols-2 gap-3 border-b border-slate-200 px-4 py-3 md:grid-cols-6">
        <input className="input" name="q" defaultValue={q} placeholder="Search label / notes / actor…" />
        <select className="input" name="action" defaultValue={action}>
          <option value="">All actions</option>
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <input className="input" name="entity" defaultValue={entity} placeholder="Entity (e.g. masters.item)" />
        <input className="input" type="date" name="date_from" defaultValue={dateFrom} />
        <input className="input" type="date" name="date_to" defaultValue={dateTo} />
        <button type="submit" className="btn-primary">
          Apply
        </button>
      </form>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="px-4 py-2 font-medium">When</th>
              <th className="px-4 py-2 font-medium">Action</th>
              <th className="px-4 py-2 font-medium">Actor</th>
              <th className="px-4 py-2 font-medium">Entity</th>
              <th className="px-4 py-2 font-medium">Label</th>
              <th className="px-4 py-2 font-medium">IP</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-400">
                  No log entries match your filters.
                </td>
              </tr>
            ) : (
              data.items.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2 text-slate-500">{row.created_at}</td>
                  <td className="px-4 py-2">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">{row.action_label || row.action}</span>
                  </td>
                  <td className="px-4 py-2">{row.actor_username || <span className="text-slate-400">System</span>}</td>
                  <td className="px-4 py-2 text-slate-500">{row.entity_type}</td>
                  <td className="px-4 py-2">{row.entity_label || <span className="text-slate-400">—</span>}</td>
                  <td className="px-4 py-2 text-slate-500">{row.ip_address || "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-slate-200 px-4 py-2 text-sm text-slate-500">
        <span>
          {data.pagination.total} entries
        </span>
        <div className="flex items-center gap-2">
          <span>Page {page} of {Math.max(1, data.pagination.pages)}</span>
        </div>
      </div>
    </div>
  );
}