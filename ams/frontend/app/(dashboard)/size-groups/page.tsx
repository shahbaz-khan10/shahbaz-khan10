import MasterScreen from "@/components/MasterScreen";

export default async function SizeGroupsPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Size Groups"
      path="/size-groups"
      thing="size_group"
      searchParams={searchParams}
      columns={[{ key: "name", label: "Name" }]}
      fields={[
        { name: "name", label: "Name", required: true },
        { name: "size_ids", label: "Sizes", type: "multiselect" },
      ]}
      optionFields={{ size_ids: { endpoint: "/sizes", labelKey: "name" } }}
    />
  );
}