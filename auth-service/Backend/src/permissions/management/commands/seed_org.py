"""Seed departments, designations, helper worker profiles and the super admin user."""

import os
import re
from datetime import date

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

DEPARTMENTS = [
    ("EXEC", "Executive"),
    ("ADMIN", "Admin & HR"),
    ("MERCH", "Merchandising"),
    ("PURCH", "Purchase"),
    ("FAB", "Fabric & Store"),
    ("ACC", "Accounts"),
    ("CUT", "Cutting"),
    ("SEW", "Sewing"),
    ("QMS", "Quality"),
    ("FIN", "Finishing"),
    ("PKG", "Packing"),
    ("MAINT", "Maintenance"),
    ("GAR", "Garments"),
    ("FNL", "Finance"),
    ("IT", "IT"),
    ("PROTO", "Prototype"),
    ("PLANN", "Planning"),
    ("DY", "Dyeing"),
    ("PRNT", "Printing"),
    ("SAFETY", "Security"),
    ("WELF", "Labour Welfare"),
    ("COMP", "Compliance"),
    ("LOG", "Logistics"),
    ("C&F", "Clearing & Forwarding"),
    ("SMPL", "Sample"),
    ("INT", "Internal Audit"),
]

DESIGNATIONS = [
    "Managing Director",
    "GM - Operations",
    "GM - Merchandising",
    "GM - Admin",
    "Department Head",
    "Senior Merchandiser",
    "Merchandiser",
    "Assistant Merchandiser",
    "Production Manager",
    "Assistant Production Manager",
    "Line Supervisor",
    "Line Leader",
    "Cutting Master",
    "Spreader",
    "Quality Incharge",
    "QC Inspector",
    "Store Incharge",
    "Store Keeper",
    "Fabric Store Keeper",
    "Purchase Officer",
    "Accounts Officer",
    "Costing Executive",
    "HR Officer",
    "Labour Welfare Officer",
    "Maintenance Supervisor",
    "Electrician",
    "Machine Operator",
    "Helper",
    "Cutting Helper",
    "Sewing Operator",
    "Packing Operator",
    "Finishing Operator",
    "Security Guard",
    "Driver",
    "Peon",
]


class Command(BaseCommand):
    help = "Seed default departments, designations and the platform super admin (idempotent)."

    def handle(self, *args, **options):
        Department = apps.get_model("employees", "Department")
        Designation = apps.get_model("employees", "Designation")
        Employee = apps.get_model("employees", "Employee")

        for code, name in DEPARTMENTS:
            Department.objects.update_or_create(code=code.upper(), defaults={"name": name})

        for name in DESIGNATIONS:
            code = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
            Designation.objects.update_or_create(code=code, defaults={"name": name})

        admin_dept = Department.objects.filter(code="ADMIN").first()
        md_designation = Designation.objects.filter(name="Managing Director").first()
        if not Employee.objects.all().exists():
            Employee.objects.create(
                employee_code="EMP-0001",
                full_name="Factory Administrator",
                cnic="0000000000000",
                gender="M",
                joining_date=date(2024, 1, 1),
                department=admin_dept,
                designation=md_designation,
            )

        User = get_user_model()
        username = os.getenv("SUPER_ADMIN_USERNAME", "admin")
        password = os.getenv("SUPER_ADMIN_PASSWORD", "SuperAdmin@123")
        email = os.getenv("SUPER_ADMIN_EMAIL", "admin@fct.local")
        employee = Employee.objects.first()
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username, email=email, is_active=True, is_super_admin=True, employee=employee)
            user.set_password(password)
            user.save()
        else:
            user.is_active = True
            user.is_super_admin = True
            if not user.employee_id and employee:
                user.employee_id = employee.id
            user.save()

        Role = apps.get_model("permissions", "Role")
        EmployeeRole = apps.get_model("permissions", "EmployeeRole")
        sa_role = Role.objects.filter(name="Super Admin").first()
        if sa_role and not EmployeeRole.objects.filter(user=user, role=sa_role).exists():
            EmployeeRole.objects.create(user=user, role=sa_role)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(DEPARTMENTS)} departments, {len(DESIGNATIONS)} designations and super admin '{username}'."))