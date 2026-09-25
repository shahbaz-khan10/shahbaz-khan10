export interface MenuItem {
  href: string;
  label: string;
  perm: string;
  icon: string;
}

export const MENU: MenuItem[] = [
  { href: "/", label: "Dashboard", perm: "ams.dashboard.view", icon: "▦" },
  { href: "/departments", label: "Departments", perm: "ams.department.view", icon: "▣" },
  { href: "/designations", label: "Designations", perm: "ams.designation.view", icon: "▣" },
  { href: "/lines", label: "Production Lines", perm: "ams.production_line.view", icon: "⛓" },
  { href: "/employees", label: "Employees", perm: "ams.employee.view", icon: "🧑" },
  { href: "/buyers", label: "Buyers", perm: "ams.buyer.view", icon: "🛒" },
  { href: "/suppliers", label: "Suppliers", perm: "ams.supplier.view", icon: "🚚" },
  { href: "/item-categories", label: "Item Categories", perm: "ams.item_category.view", icon: "🗂" },
  { href: "/items", label: "Items", perm: "ams.item.view", icon: "🧵" },
  { href: "/units-of-measure", label: "Units of Measure", perm: "ams.unit_of_measure.view", icon: "⚖" },
  { href: "/uom-conversions", label: "UoM Conversions", perm: "ams.uom_conversion.view", icon: "⇄" },
  { href: "/colors", label: "Colors", perm: "ams.color.view", icon: "🎨" },
  { href: "/sizes", label: "Sizes", perm: "ams.size.view", icon: "📏" },
  { href: "/size-groups", label: "Size Groups", perm: "ams.size_group.view", icon: "📊" },
  { href: "/currencies", label: "Currencies", perm: "ams.currency.view", icon: "💱" },
  { href: "/exchange-rates", label: "Exchange Rates", perm: "ams.exchange_rate.view", icon: "⇅" },
  { href: "/warehouses", label: "Warehouses", perm: "ams.warehouse.view", icon: "🏬" },
  { href: "/users", label: "Users & Access", perm: "ams.user.view", icon: "🔐" },
  { href: "/roles", label: "Roles & Permissions", perm: "ams.role.view", icon: "🛡" },
  { href: "/audit", label: "Audit Logs", perm: "ams.audit.view", icon: "🧾" },
];

export function can(perms: string[], codename: string): boolean {
  if (!perms || perms.length === 0) return false;
  return perms.includes(codename);
}