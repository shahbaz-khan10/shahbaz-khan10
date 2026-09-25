export interface UserPayload {
  id: number;
  username: string;
  email: string | null;
  full_name: string;
  employee: {
    id: number;
    employee_code: string;
    department: string | null;
    department_id: number | null;
    designation: string | null;
    designation_id: number | null;
  } | null;
  is_super_admin: boolean;
  is_active: boolean;
  roles: string[];
  perms: string[];
}

export type FieldType =
  | "text"
  | "number"
  | "date"
  | "textarea"
  | "checkbox"
  | "select"
  | "multiselect"
  | "password";

export interface FieldDef {
  name: string;
  label: string;
  type?: FieldType;
  required?: boolean;
  options?: { value: string; label: string }[];
  onCreateOnly?: boolean;
  help?: string;
}

export interface ColumnDef {
  key: string;
  label: string;
  render?: (row: Record<string, unknown>) => string | number;
}