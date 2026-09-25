import MasterScreen from "@/components/MasterScreen";

export default async function SizesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Sizes"
      path="/sizes"
      thing="size"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "sort_order", label: "Order" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "sort_order", label: "Sort order", type: "number" },
      ]}
    />
  );
}