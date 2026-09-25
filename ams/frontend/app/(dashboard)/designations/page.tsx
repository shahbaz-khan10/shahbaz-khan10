import MasterScreen from "@/components/MasterScreen";

export default async function DesignationsPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Designations"
      path="/designations"
      thing="designation"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "department_name", label: "Department" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "department_id", label: "Department", type: "select" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{ department_id: { endpoint: "/departments", labelKey: "name" } }}
    />
  );
}