import MasterScreen from "@/components/MasterScreen";

export default async function LinesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Production Lines"
      path="/production-lines"
      thing="production_line"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "floor", label: "Floor" },
        { key: "capacity_pcs", label: "Capacity (pcs)" },
        { key: "supervisor_name", label: "Supervisor" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "floor", label: "Floor" },
        { name: "capacity_pcs", label: "Capacity (pcs)", type: "number" },
        { name: "supervisor_id", label: "Supervisor", type: "select" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{ supervisor_id: { endpoint: "/employees", labelKey: "full_name" } }}
    />
  );
}