import MasterScreen from "@/components/MasterScreen";

export default async function WarehousesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Warehouses"
      path="/warehouses"
      thing="warehouse"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "type", label: "Type" },
        { key: "location", label: "Location" },
        { key: "manager_name", label: "Manager" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "type", label: "Type", type: "select", options: [
          { value: "fabric_store", label: "Fabric store" },
          { value: "trims_store", label: "Trims store" },
          { value: "general_store", label: "General store" },
          { value: "finished_goods_store", label: "Finished goods store" },
          { value: "raw_material_store", label: "Raw material store" },
          { value: "other", label: "Other" },
        ] },
        { name: "location", label: "Location" },
        { name: "address", label: "Address", type: "textarea" },
        { name: "manager_id", label: "Manager", type: "select" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{ manager_id: { endpoint: "/employees", labelKey: "full_name" } }}
    />
  );
}