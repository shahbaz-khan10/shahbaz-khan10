import { api, type Paginated } from "@/lib/core";
import type { FieldDef } from "@/lib/types";
import { notFound } from "next/navigation";

import MasterScreen from "@/components/MasterScreen";
import PermsEditor, { type PermCatalogItem, type RoleBrief } from "@/components/PermsEditor";
import { can } from "@/lib/menus";
import { getUser } from "@/lib/user";

export default async function RolesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  const user = await getUser();
  if (!user) notFound();
  const canManage = can(user.perms, "ams.role.manage");

  const rolePage = (
    <MasterScreen
      title="Roles & Permissions"
      path="/roles"
      thing="role"
      searchParams={searchParams}
      columns={[
        { key: "name", label: "Name" },
        { key: "description", label: "Description" },
        { key: "permission_count", label: "Permissions" },
        { key: "user_count", label: "Users" },
        { key: "is_system", label: "System" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "name", label: "Name", required: true },
        { name: "description", label: "Description", type: "textarea" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );

  if (!canManage) return rolePage;

  const [permData, roleData] = await Promise.all([
    api<PermCatalogItem[]>("/permissions"),
    api<Paginated<Record<string, unknown>>>("/roles?page_size=200"),
  ]);

  const roles: RoleBrief[] = roleData.items.map((r) => ({
    id: Number(r.id),
    name: String(r.name),
    isSystem: Boolean(r.is_system),
    permissionIds: [], // loaded per role below
  }));

  await Promise.all(
    roles.map(async (role) => {
      const detail = await api<{ permissions: number[] }>(`/roles/${role.id}`);
      role.permissionIds = detail.permissions ?? [];
    }),
  );

  return (
    <>
      {rolePage}
      <PermsEditor roles={roles} catalog={permData} />
    </>
  );
}