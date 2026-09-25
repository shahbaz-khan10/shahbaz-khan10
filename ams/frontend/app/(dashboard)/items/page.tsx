import MasterScreen from "@/components/MasterScreen";

export default async function ItemsPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Items"
      path="/items"
      thing="item"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "category_name", label: "Category" },
        { key: "unit_code", label: "Unit" },
        { key: "purchase_price", label: "Purchase" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "description", label: "Description", type: "textarea" },
        { name: "category_id", label: "Category", type: "select", required: true },
        { name: "unit_id", label: "Unit", type: "select", required: true },
        { name: "color_id", label: "Color", type: "select" },
        { name: "supplier_id", label: "Supplier", type: "select" },
        { name: "purchase_price", label: "Purchase price", type: "number" },
        { name: "sale_price", label: "Sale price", type: "number" },
        { name: "reorder_level", label: "Reorder level", type: "number" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{
        category_id: { endpoint: "/item-categories", labelKey: "name" },
        unit_id: { endpoint: "/units-of-measure", labelKey: "code" },
        color_id: { endpoint: "/colors", labelKey: "name" },
        supplier_id: { endpoint: "/suppliers", labelKey: "name" },
      }}
    />
  );
}