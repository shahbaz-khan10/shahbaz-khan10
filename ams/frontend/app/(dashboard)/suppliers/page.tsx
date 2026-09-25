import MasterScreen from "@/components/MasterScreen";

export default async function SuppliersPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Suppliers"
      path="/suppliers"
      thing="supplier"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "type", label: "Type" },
        { key: "contact_person", label: "Contact" },
        { key: "country", label: "Country" },
        { key: "currency_code", label: "Currency" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "type", label: "Type", type: "select", options: [
          { value: "fabric", label: "Fabric" },
          { value: "trims", label: "Trims & Accessories" },
          { value: "services", label: "Services" },
          { value: "packaging", label: "Packaging" },
          { value: "general", label: "General" },
        ] },
        { name: "contact_person", label: "Contact person" },
        { name: "contact_phone", label: "Phone" },
        { name: "email", label: "Email" },
        { name: "address", label: "Address", type: "textarea" },
        { name: "country", label: "Country" },
        { name: "city", label: "City" },
        { name: "currency_id", label: "Currency", type: "select" },
        { name: "payment_terms", label: "Payment terms" },
        { name: "ntn", label: "NTN" },
        { name: "gst", label: "GST" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{ currency_id: { endpoint: "/currencies", labelKey: "code" } }}
    />
  );
}