import { notFound } from "next/navigation";

import Table from "@/components/Table";
import { api, type Paginated } from "@/lib/core";
import { can } from "@/lib/menus";
import type { ColumnDef, FieldDef } from "@/lib/types";
import { getUser } from "@/lib/user";

export interface OptionSource {
  endpoint: string;
  labelKey?: string;
}

export interface MasterScreenProps {
  title: string;
  description?: string;
  path: string;
  thing: string;
  columns: ColumnDef[];
  fields: FieldDef[];
  optionFields?: Record<string, OptionSource>;
  searchParams?: { q?: string | string[]; page?: string | string[] };
}

export default async function MasterScreen({
  title,
  description,
  path,
  thing,
  columns,
  fields,
  optionFields,
  searchParams,
}: MasterScreenProps) {
  const user = await getUser();
  if (!user) notFound();

  const q = Array.isArray(searchParams?.q) ? searchParams!.q[0] : (searchParams?.q ?? "");
  const page = Math.max(1, Number(Array.isArray(searchParams?.page) ? searchParams!.page[0] : (searchParams?.page ?? "1")) || 1);

  const gates = {
    view: can(user.perms, `ams.${thing}.view`),
    create: can(user.perms, `ams.${thing}.create`),
    edit: can(user.perms, `ams.${thing}.edit`),
    delete: can(user.perms, `ams.${thing}.delete`),
  };

  if (!gates.view) {
    return (
      <div className="card p-10 text-center text-slate-500">
        You do not have the <code>ams.{thing}.view</code> permission.
      </div>
    );
  }

  const query = new URLSearchParams({ page: String(page), page_size: "20" });
  if (q) query.set("search", q);

  const data = await api<Paginated<Record<string, unknown>>>(`${path}?${query.toString()}`);

  const fieldOptions: Record<string, { value: string; label: string }[]> = {};
  if (optionFields) {
    for (const [field, src] of Object.entries(optionFields)) {
      try {
        const res = await api<Paginated<Record<string, unknown>>>(`${src.endpoint}?page_size=200`);
        const labelKey = src.labelKey || "name";
        fieldOptions[field] = res.items.map((it) => ({
          value: String(it.id),
          label: String(it[labelKey] ?? it.code ?? it.name ?? it.id),
        }));
      } catch {
        fieldOptions[field] = [];
      }
    }
  }

  return (
    <Table
      path={path}
      title={title}
      description={description}
      columns={columns}
      fields={fields}
      fieldOptions={fieldOptions}
      items={data.items}
      page={page}
      pages={data.pagination.pages}
      total={data.pagination.total}
      search={q}
      gates={gates}
    />
  );
}