import MasterScreen from "@/components/MasterScreen";

export default async function UnitsPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Units of Measure"
      path="/units-of-measure"
      thing="unit_of_measure"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "dimension", label: "Dimension" },
        { key: "is_base", label: "Base" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "dimension", label: "Dimension", type: "select", options: [
          { value: "count", label: "Count" },
          { value: "length", label: "Length" },
          { value: "weight", label: "Weight" },
          { value: "volume", label: "Volume" },
          { value: "area", label: "Area" },
          { value: "other", label: "Other" },
        ] },
        { name: "is_base", label: "Base unit", type: "checkbox" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}