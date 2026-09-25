from django.db import models

from common.base import SoftDeleteModel


class CompanyProfile(SoftDeleteModel):
    """Single-factory profile. Exactly one active row at a time."""

    singleton_key = models.CharField(max_length=16, default="factory", unique=True)
    company_name = models.CharField(max_length=200)
    factory_name = models.CharField(max_length=200, blank=True, default="")
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    website = models.CharField(max_length=200, blank=True, default="")
    registration_no = models.CharField(max_length=64, blank=True, default="")
    ntn = models.CharField(max_length=32, blank=True, default="")
    gst = models.CharField(max_length=32, blank=True, default="")
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1, help_text="1=Jan … 12=Dec")
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Company Profile"

    def __str__(self):
        return self.company_name


class Department(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Designation(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="designations"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductionLine(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    floor = models.CharField(max_length=64, blank=True, default="")
    capacity_pcs = models.PositiveIntegerField(default=0)
    supervisor = models.ForeignKey(
        "Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="supervised_lines"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(SoftDeleteModel):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    EMPLOYMENT_TYPE_CHOICES = [
        ("permanent", "Permanent"),
        ("contract", "Contract"),
        ("daily_wage", "Daily Wage"),
        ("intern", "Intern"),
    ]

    employee_code = models.CharField(max_length=32, unique=True)
    full_name = models.CharField(max_length=200)
    cnic = models.CharField(max_length=15, unique=True, null=True, blank=True)
    personal_phone = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name="employees")
    joining_date = models.DateField(null=True, blank=True)
    reporting_manager = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="team_members"
    )
    employment_type = models.CharField(
        max_length=16, choices=EMPLOYMENT_TYPE_CHOICES, default="permanent"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_name"]
        indexes = [models.Index(fields=["department"]), models.Index(fields=["designation"])]

    def __str__(self):
        return f"{self.employee_code} — {self.full_name}"