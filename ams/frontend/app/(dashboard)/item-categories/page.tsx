import MasterScreen from "@/components/MasterScreen";

export default async function ItemCategoriesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Item Categories"
      path="/item-categories"
      thing="item_category"
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
        { name: "parent_id", label: "Parent category", type: "select" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{ parent_id: { endpoint: "/item-categories", labelKey: "name" } }}
    />
  );
}