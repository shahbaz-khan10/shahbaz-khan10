import MasterScreen from "@/components/MasterScreen";

export default async function DepartmentsPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Departments"
      path="/departments"
      thing="department"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "parent_name", label: "Parent" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "parent_id", label: "Parent department", type: "select" },
        { name: "description", label: "Description", type: "textarea" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{ parent_id: { endpoint: "/departments", labelKey: "name" } }}
    />
  );
}