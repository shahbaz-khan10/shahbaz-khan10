import MasterScreen from "@/components/MasterScreen";

export default async function EmployeesPage({ searchParams }: { searchParams?: { q?: string | string[]; page?: string | string[] } }) {
  return (
    <MasterScreen
      title="Employees"
      path="/employees"
      thing="employee"
      searchParams={searchParams}
      columns={[
        { key: "employee_code", label: "Code" },
        { key: "full_name", label: "Name" },
        { key: "department_name", label: "Department" },
        { key: "designation_name", label: "Designation" },
        { key: "employment_type", label: "Type" },
        { key: "is_active", label: "Active" },
      ]}
      fields={[
        { name: "employee_code", label: "Employee code" },
        { name: "full_name", label: "Full name", required: true },
        { name: "cnic", label: "CNIC" },
        { name: "personal_phone", label: "Phone" },
        { name: "email", label: "Email" },
        { name: "gender", label: "Gender", type: "select", options: [{ value: "M", label: "Male" }, { value: "F", label: "Female" }, { value: "O", label: "Other" }] },
        { name: "department_id", label: "Department", type: "select", required: true },
        { name: "designation_id", label: "Designation", type: "select", required: true },
        { name: "joining_date", label: "Joining date", type: "date" },
        { name: "reporting_manager_id", label: "Reporting manager", type: "select" },
        { name: "employment_type", label: "Employment type", type: "select", options: [
          { value: "permanent", label: "Permanent" },
          { value: "contract", label: "Contract" },
          { value: "daily_wage", label: "Daily wage" },
          { value: "intern", label: "Intern" },
        ] },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
      optionFields={{
        department_id: { endpoint: "/departments", labelKey: "name" },
        designation_id: { endpoint: "/designations", labelKey: "name" },
        reporting_manager_id: { endpoint: "/employees", labelKey: "full_name" },
      }}
    />
  );
}