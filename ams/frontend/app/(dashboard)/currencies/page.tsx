import MasterScreen from "@/components/MasterScreen";

export default async function CurrenciesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Currencies"
      path="/currencies"
      thing="currency"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "symbol", label: "Symbol" },
        { key: "is_base", label: "Base" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "symbol", label: "Symbol" },
        { name: "is_base", label: "Base (reporting) currency", type: "checkbox" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}