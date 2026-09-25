import MasterScreen from "@/components/MasterScreen";

export default async function BuyersPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Buyers"
      path="/buyers"
      thing="buyer"
      searchParams={searchParams}
      columns={[
        { key: "code", label: "Code" },
        { key: "name", label: "Name" },
        { key: "contact_person", label: "Contact" },
        { key: "country", label: "Country" },
        { key: "currency_code", label: "Currency" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "contact_person", label: "Contact person" },
        { name: "contact_phone", label: "Phone" },
        { name: "email", label: "Email" },
        { name: "country", label: "Country" },
        { name: "city", label: "City" },
        { name: "currency_id", label: "Currency", type: "select" },
        { name: "payment_terms", label: "Payment terms" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{ currency_id: { endpoint: "/currencies", labelKey: "code" } }}
    />
  );
}