"""Seed the service / permission / role catalog for the AMS module."""

from django.apps import apps
from django.core.management.base import BaseCommand

SERVICES = [
    ("ams", "Admin & Master System"),
    ("mms", "Merchandising Management System"),
]

CATALOG = {
    "ams": [
        ("dashboard", ["view"], "Dashboard"),
        ("company_profile", ["view", "edit"], "Company profile"),
        ("department", ["view", "create", "edit", "delete"], "Department"),
        ("designation", ["view", "create", "edit", "delete"], "Designation"),
        ("production_line", ["view", "create", "edit", "delete"], "Production line"),
        ("employee", ["view", "create", "edit", "delete"], "Employee"),
        ("currency", ["view", "create", "edit", "delete"], "Currency"),
        ("exchange_rate", ["view", "create", "edit", "delete"], "Exchange rate"),
        ("buyer", ["view", "create", "edit", "delete"], "Buyer"),
        ("supplier", ["view", "create", "edit", "delete"], "Supplier"),
        ("item_category", ["view", "create", "edit", "delete"], "Item category"),
        ("item", ["view", "create", "edit", "delete", "approve"], "Item"),
        ("unit_of_measure", ["view", "create", "edit", "delete"], "Unit of measure"),
        ("uom_conversion", ["view", "create", "edit", "delete"], "UoM conversion"),
        ("color", ["view", "create", "edit", "delete"], "Color"),
        ("size", ["view", "create", "edit", "delete"], "Size"),
        ("size_group", ["view", "create", "edit", "delete"], "Size group"),
        ("warehouse", ["view", "create", "edit", "delete"], "Warehouse"),
        ("user", ["view", "create", "edit", "delete"], "User"),
        ("role", ["view", "create", "edit", "delete", "manage"], "Role"),
        ("audit", ["view", "create"], "Audit logs"),
    ],
    "mms": [
        ("dashboard", ["view"], "Merchandising dashboard"),
        ("style", ["view", "create", "edit", "delete"], "Style"),
        ("order", ["view", "create", "edit", "delete", "approve"], "Buyer order"),
        ("bom", ["view", "create", "edit", "delete", "approve"], "Bill of materials"),
        ("costing", ["view", "create", "edit", "delete", "approve"], "Costing"),
        ("sample", ["view", "create", "edit", "delete"], "Sample tracking"),
        ("report", ["view"], "Merchandising reports"),
    ],
}


def _role_codename(service, entity, action):
    return f"{service}.{entity}.{action}"


ROLES = {
    "Super Admin": {
        "description": "Built-in system role granted to platform super admins.",
        "permissions": "ALL",
    },
    "Admin": {
        "description": "Full access to all AMS features.",
        "permissions": "ALL",
    },
    "Merchandiser": {
        "description": "Works with buyers, items and order planning.",
        "permissions": [
            "ams.dashboard.view",
            "ams.company_profile.view",
            "ams.buyer.view", "ams.buyer.create", "ams.buyer.edit",
            "ams.supplier.view", "ams.supplier.create", "ams.supplier.edit",
            "ams.item_category.view", "ams.item_category.create", "ams.item_category.edit",
            "ams.item.view", "ams.item.create", "ams.item.edit", "ams.item.approve",
            "ams.unit_of_measure.view",
            "ams.uom_conversion.view", "ams.uom_conversion.create",
            "ams.color.view", "ams.size.view", "ams.size_group.view",
            "ams.currency.view", "ams.exchange_rate.view",
            "ams.warehouse.view",
            "ams.audit.create",
            "mms.dashboard.view",
            "mms.style.view", "mms.style.create", "mms.style.edit", "mms.style.delete",
            "mms.order.view", "mms.order.create", "mms.order.edit", "mms.order.delete", "mms.order.approve",
            "mms.bom.view", "mms.bom.create", "mms.bom.edit", "mms.bom.delete", "mms.bom.approve",
            "mms.costing.view", "mms.costing.create", "mms.costing.edit", "mms.costing.delete", "mms.costing.approve",
            "mms.sample.view", "mms.sample.create", "mms.sample.edit", "mms.sample.delete",
            "mms.report.view",
        ],
    },
    "Store Keeper": {
        "description": "Manages inventory masters and warehouse records.",
        "permissions": [
            "ams.dashboard.view",
            "ams.item.view", "ams.item.create", "ams.item.edit",
            "ams.warehouse.view", "ams.warehouse.edit",
            "ams.unit_of_measure.view", "ams.uom_conversion.view",
            "ams.color.view", "ams.size.view",
            "ams.currency.view", "ams.exchange_rate.view",
            "ams.supplier.view",
        ],
    },
    "Production Manager": {
        "description": "Oversees production lines and floor staffing.",
        "permissions": [
            "ams.dashboard.view",
            "ams.department.view",
            "ams.designation.view",
            "ams.production_line.view", "ams.production_line.edit",
            "ams.employee.view",
            "ams.item.view",
            "ams.color.view",
            "ams.size.view",
            "ams.warehouse.view",
            "mms.dashboard.view",
            "mms.style.view",
            "mms.order.view",
            "mms.bom.view",
            "mms.costing.view",
            "mms.sample.view",
            "mms.report.view",
        ],
    },
    "Line Supervisor": {
        "description": "Manages a single production line on the floor.",
        "permissions": [
            "ams.dashboard.view",
            "ams.production_line.view",
            "ams.employee.view",
            "ams.item.view",
        ],
    },
    "QC Inspector": {
        "description": "Quality inspection personnel.",
        "permissions": [
            "ams.dashboard.view",
            "ams.item.view",
            "mms.dashboard.view",
            "mms.sample.view",
        ],
    },
    "HR Officer": {
        "description": "Maintains employee and organizational records.",
        "permissions": [
            "ams.dashboard.view",
            "ams.department.view", "ams.department.create", "ams.department.edit",
            "ams.designation.view", "ams.designation.create", "ams.designation.edit",
            "ams.employee.view", "ams.employee.create", "ams.employee.edit",
        ],
    },
    "Accountant": {
        "description": "Financial & currency related master data.",
        "permissions": [
            "ams.dashboard.view",
            "ams.company_profile.view",
            "ams.currency.view", "ams.currency.create", "ams.currency.edit",
            "ams.exchange_rate.view", "ams.exchange_rate.create", "ams.exchange_rate.edit",
            "ams.buyer.view", "ams.supplier.view",
            "mms.dashboard.view",
            "mms.order.view",
            "mms.style.view",
            "mms.costing.view",
            "mms.report.view",
        ],
    },
    "Viewer": {
        "description": "Read-only access across AMS.",
        "permissions": [
            "ams.dashboard.view",
            "ams.company_profile.view",
            "ams.department.view",
            "ams.designation.view",
            "ams.production_line.view",
            "ams.employee.view",
            "ams.currency.view",
            "ams.exchange_rate.view",
            "ams.buyer.view",
            "ams.supplier.view",
            "ams.item_category.view",
            "ams.item.view",
            "ams.unit_of_measure.view",
            "ams.uom_conversion.view",
            "ams.color.view",
            "ams.size.view",
            "ams.size_group.view",
            "ams.warehouse.view",
            "mms.dashboard.view",
            "mms.style.view",
            "mms.order.view",
            "mms.bom.view",
            "mms.costing.view",
            "mms.sample.view",
            "mms.report.view",
        ],
    },
}


class Command(BaseCommand):
    help = "Seed services, permission catalog and default roles (idempotent)."

    def handle(self, *args, **options):
        Service = apps.get_model("permissions", "Service")
        Permission = apps.get_model("permissions", "Permission")
        Role = apps.get_model("permissions", "Role")
        RolePermission = apps.get_model("permissions", "RolePermission")

        services = {}
        for code, name in SERVICES:
            svc, _ = Service.objects.get_or_create(code=code, defaults={"name": name})
            services[code] = svc

        all_perms = []
        for svc_code, entries in CATALOG.items():
            for entity, actions, label in entries:
                for action in actions:
                    codename = _role_codename(svc_code, entity, action)
                    perm, created = Permission.objects.update_or_create(
                        codename=codename,
                        defaults={
                            "module": services[svc_code],
                            "entity": entity,
                            "action": action,
                            "name": f"{label} - {action}",
                        },
                    )
                    all_perms.append(perm.id)

        perm_ids = set(all_perms)
        perm_map = {
            p["codename"]: p["id"]
            for p in Permission.objects.filter(id__in=perm_ids).values("id", "codename")
        }

        for name, cfg in ROLES.items():
            role, _ = Role.objects.update_or_create(
                name=name,
                defaults={"description": cfg["description"], "is_system": True, "is_active": True},
            )
            if cfg["permissions"] == "ALL":
                role_perms = perm_ids
            else:
                unknown = set(cfg["permissions"]) - set(perm_map)
                if unknown:
                    self.stderr.write(self.style.WARNING(f"Role '{name}' references unknown permissions: {sorted(unknown)}"))
                role_perms = {perm_map[c] for c in cfg["permissions"] if c in perm_map}
            RolePermission.objects.filter(role=role).exclude(permission_id__in=role_perms).delete()
            existing = set(RolePermission.objects.filter(role=role).values_list("permission_id", flat=True))
            RolePermission.objects.bulk_create(
                [RolePermission(role=role, permission_id=pid) for pid in role_perms - existing],
                ignore_conflicts=True,
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(all_perms)} permissions across {len(SERVICES)} service(s) and {len(ROLES)} roles."))