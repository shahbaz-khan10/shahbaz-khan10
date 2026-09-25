import MasterScreen from "@/components/MasterScreen";

export default async function ColorsPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Colors"
      path="/colors"
      thing="color"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "hex", label: "Hex" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "hex", label: "Hex color", help: "e.g. #2f6fed" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}