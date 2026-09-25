import MasterScreen from "@/components/MasterScreen";

export default async function UomConversionsPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="UoM Conversions"
      path="/uom-conversions"
      thing="uom_conversion"
      searchParams={searchParams}
      columns={[
        { key: "from_uom_code", label: "From" },
        { key: "to_uom_code", label: "To" },
        { key: "factor", label: "Factor" },
      ]}
      fields={[
        { name: "from_uom_id", label: "From unit", type: "select", required: true },
        { name: "to_uom_id", label: "To unit", type: "select", required: true },
        { name: "factor", label: "Factor (1 from = factor to)", type: "number", required: true },
      ]}
      optionFields={{
        from_uom_id: { endpoint: "/units-of-measure", labelKey: "code" },
        to_uom_id: { endpoint: "/units-of-measure", labelKey: "code" },
      }}
    />
  );
}