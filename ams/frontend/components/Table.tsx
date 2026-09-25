"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";

import { deleteRecord, getRecord, saveRecord } from "@/lib/actions";
import type { ColumnDef, FieldDef } from "@/lib/types";

export interface FieldOptions {
  [fieldName: string]: { value: string; label: string }[];
}

export interface TableProps {
  path: string;
  title: string;
  description?: string;
  columns: ColumnDef[];
  fields: FieldDef[];
  fieldOptions?: FieldOptions;
  items: Record<string, unknown>[];
  page: number;
  pages: number;
  total: number;
  search?: string;
  gates: { view: boolean; create: boolean; edit: boolean; delete: boolean };
  canDelete?: (row: Record<string, unknown>) => boolean;
  rowLabel?: (row: Record<string, unknown>) => string;
}

export default function Table({
  path,
  title,
  description,
  columns,
  fields,
  fieldOptions,
  items,
  page,
  pages,
  total,
  search = "",
  gates,
  canDelete,
  rowLabel,
}: TableProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();
  const [query, setQuery] = useState(search);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setQuery(search);
  }, [search]);

  const applySearch = useCallback(
    (value: string) => {
      if (debounce.current) clearTimeout(debounce.current);
      debounce.current = setTimeout(() => {
        const params = new URLSearchParams();
        if (value) params.set("q", value);
        router.push(`${pathname}?${params.toString()}`);
      }, 350);
    },
    [pathname, router],
  );

  function goPage(p: number) {
    const params = new URLSearchParams();
    if (search) params.set("q", search);
    params.set("page", String(p));
    router.push(`${pathname}?${params.toString()}`);
  }

  function resetValues() {
    const next: Record<string, unknown> = {};
    for (const f of fields) {
      next[f.name] = f.type === "checkbox" ? false : "";
    }
    setValues(next);
  }

  async function openCreate() {
    setEditingId(null);
    resetValues();
    setMessage("");
    setOpen(true);
  }

  async function openEdit(row: Record<string, unknown>) {
    setLoading(true);
    setMessage("");
    const record = await getRecord(path, Number(row.id));
    if ("error" in (record as object)) {
      setMessage(String((record as { error: string }).error));
      setLoading(false);
      return;
    }
    const next: Record<string, unknown> = {};
    for (const f of fields) {
      const isCheckbox = f.type === "checkbox";
      const raw = (record as Record<string, unknown>)[f.name];
      next[f.name] = isCheckbox ? Boolean(raw) : raw ?? (isCheckbox ? false : "");
    }
    setValues(next);
    setEditingId(Number(row.id));
    setOpen(true);
    setLoading(false);
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    const outcome = await saveRecord(path, editingId, values);
    if (outcome.ok) {
      setOpen(false);
      router.refresh();
    } else {
      setMessage(outcome.error || "Save failed.");
    }
  }

  function onDelete(row: Record<string, unknown>) {
    if (!window.confirm(`Delete "${rowLabel ? rowLabel(row) : row.id}"? This cannot be undone.`)) return;
    void deleteRecord(path, Number(row.id)).then((outcome) => {
      if (outcome.ok) router.refresh();
      else setMessage(outcome.error || "Delete failed.");
    });
  }

  return (
    <div className="card">
      {message && !open ? (
        <div className="flex items-center justify-between gap-2 border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          <span>{message}</span>
          <button type="button" onClick={() => setMessage("")} className="font-semibold">
            ✕
          </button>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
          {description ? <p className="text-sm text-slate-500">{description}</p> : null}
        </div>
        <div className="flex items-center gap-2">
          <input
            className="input w-56"
            placeholder="Search…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              applySearch(e.target.value);
            }}
          />
          {gates.create ? (
            <button type="button" className="btn-primary" onClick={openCreate}>
              + New
            </button>
          ) : null}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              {columns.map((c) => (
                <th key={c.key} className="px-4 py-2 font-medium">
                  {c.label}
                </th>
              ))}
              <th className="px-4 py-2 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1} className="px-4 py-10 text-center text-slate-400">
                  No records found.
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr key={String(row.id)} className="border-b border-slate-100 hover:bg-slate-50">
                  {columns.map((c) => (
                    <td key={c.key} className="px-4 py-2">
                      {c.render ? c.render(row) : String(row[c.key] ?? "")}
                    </td>
                  ))}
                  <td className="space-x-2 whitespace-nowrap px-4 py-2 text-right">
                    {gates.edit ? (
                      <button type="button" className="btn-secondary !px-2 !py-1" onClick={() => openEdit(row)}>
                        Edit
                      </button>
                    ) : null}
                    {gates.delete && (canDelete ? canDelete(row) : true) ? (
                      <button type="button" className="btn-danger !px-2 !py-1" onClick={() => onDelete(row)}>
                        Delete
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 px-4 py-2 text-sm text-slate-500">
        <span>
          {total} record{total === 1 ? "" : "s"}
        </span>
        <div className="flex items-center gap-2">
          <button type="button" className="btn-secondary !px-2 !py-1" disabled={page <= 1 || pending} onClick={() => goPage(page - 1)}>
            ← Prev
          </button>
          <span>
            Page {page} of {Math.max(1, pages)}
          </span>
          <button type="button" className="btn-secondary !px-2 !py-1" disabled={page >= pages || pending} onClick={() => goPage(page + 1)}>
            Next →
          </button>
        </div>
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setOpen(false)}>
          <div
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-4 text-lg font-semibold">
              {editingId ? "Edit record" : "New record"}
            </h2>
            {message ? <p className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p> : null}
            {loading ? (
              <p className="py-6 text-center text-sm text-slate-400">Loading…</p>
            ) : (
              <form onSubmit={onSubmit} className="space-y-4">
                {fields.map((f) => (
                  <FieldInput
                    key={f.name}
                    field={f}
                    value={values[f.name]}
                    editing={Boolean(editingId)}
                    options={fieldOptions?.[f.name]}
                    onChange={(name, value) => setValues((prev) => ({ ...prev, [name]: value }))}
                  />
                ))}
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary">
                    Save
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function FieldInput({
  field,
  value,
  editing,
  options,
  onChange,
}: {
  field: FieldDef;
  value: unknown;
  editing: boolean;
  options?: { value: string; label: string }[];
  onChange: (name: string, value: unknown) => void;
}) {
  const { name, label, type = "text", required, help } = field;
  const opts = options || field.options || [];

  if (field.onCreateOnly && editing) return null;

  if (type === "checkbox") {
    return (
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="h-4 w-4" checked={Boolean(value)} onChange={(e) => onChange(name, e.target.checked)} />
        {label}
        {help ? <span className="text-xs text-slate-400">{help}</span> : null}
      </label>
    );
  }

  if (type === "multiselect") {
    return (
      <div>
        <span className="label">{label}</span>
        <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-slate-200 p-2">
          {opts.length === 0 ? (
            <p className="text-xs text-slate-400">No options available.</p>
          ) : (
            opts.map((opt) => {
              const values = Array.isArray(value) ? value.map(String) : [];
              const checked = values.includes(String(opt.value));
              return (
                <label key={opt.value} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    checked={checked}
                    onChange={(e) => {
                      const next = e.target.checked ? [...values, opt.value] : values.filter((v) => v !== opt.value);
                      onChange(name, next);
                    }}
                  />
                  {opt.label}
                </label>
              );
            })
          )}
        </div>
      </div>
    );
  }

  if (type === "select") {
    return (
      <div>
        <label htmlFor={`f-${name}`} className="label">
          {label} {required ? <span className="text-red-500">*</span> : null}
        </label>
        <select id={`f-${name}`} className="input" value={String(value ?? "")} onChange={(e) => onChange(name, e.target.value)}>
          <option value="">{required ? "Select…" : "None"}</option>
          {opts.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div>
      <label htmlFor={`f-${name}`} className="label">
        {label} {required ? <span className="text-red-500">*</span> : null}
      </label>
      {type === "textarea" ? (
        <textarea
          id={`f-${name}`}
          className="input"
          rows={3}
          value={String(value ?? "")}
          onChange={(e) => onChange(name, e.target.value)}
        />
      ) : (
        <input
          id={`f-${name}`}
          className="input"
          type={type === "password" ? "password" : type}
          step={type === "number" ? "any" : undefined}
          value={String(value ?? "")}
          onChange={(e) => onChange(name, e.target.value)}
        />
      )}
      {help ? <p className="mt-1 text-xs text-slate-400">{help}</p> : null}
    </div>
  );
}