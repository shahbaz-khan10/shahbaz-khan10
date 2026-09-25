import MasterScreen from "@/components/MasterScreen";

export default async function UsersPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Users & Access"
      description="Every non-super-admin user maps to an employee and at least one role."
      path="/users"
      thing="user"
      searchParams={searchParams}
      columns={[
        { key: "username", label: "Username" },
        { key: "full_name", label: "Name" },
        { key: "employee_code", label: "Emp code" },
        { key: "department_name", label: "Department" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "username", label: "Username", required: true },
        { name: "email", label: "Email" },
        { name: "password", label: "Password", type: "password", required: true, onCreateOnly: true, help: "Minimum 8 characters" },
        { name: "employee_id", label: "Employee", type: "select", required: true, help: "Users must be linked to an employee" },
        { name: "role_ids", label: "Roles", type: "multiselect" },
        { name: "is_active", label: "Active", type: "checkbox" },
        { name: "is_super_admin", label: "Platform Super Admin", type: "checkbox", help: "Bypasses all permission checks" },
      ]}
      optionFields={{
        employee_id: { endpoint: "/employees", labelKey: "full_name" },
        role_ids: { endpoint: "/roles", labelKey: "name" },
      }}
    />
  );
}