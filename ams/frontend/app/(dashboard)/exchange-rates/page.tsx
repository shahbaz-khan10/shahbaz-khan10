import MasterScreen from "@/components/MasterScreen";

export default async function ExchangeRatesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Exchange Rates"
      path="/exchange-rates"
      thing="exchange_rate"
      searchParams={searchParams}
      columns={[
        { key: "from_currency_code", label: "From" },
        { key: "to_currency_code", label: "To" },
        { key: "rate", label: "Rate" },
        { key: "effective_date", label: "Effective" },
      ]}
      fields={[
        { name: "from_currency_id", label: "From currency", type: "select", required: true },
        { name: "to_currency_id", label: "To currency", type: "select", required: true },
        { name: "rate", label: "Rate (1 from = rate to)", type: "number", required: true },
        { name: "effective_date", label: "Effective date", type: "date", required: true },
        { name: "notes", label: "Notes" },
      ]}
      optionFields={{
        from_currency_id: { endpoint: "/currencies", labelKey: "code" },
        to_currency_id: { endpoint: "/currencies", labelKey: "code" },
      }}
    />
  );
}