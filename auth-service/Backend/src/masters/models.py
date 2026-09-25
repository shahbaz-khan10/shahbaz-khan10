from django.db import models

from common.base import SoftDeleteModel


class Currency(SoftDeleteModel):
    code = models.CharField(max_length=8, unique=True)  # PKR, USD, EUR …
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=8, blank=True, default="")
    is_base = models.BooleanField(default=False, help_text="The factory's reporting currency")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class ExchangeRate(SoftDeleteModel):
    from_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    to_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    rate = models.DecimalField(max_digits=18, decimal_places=6, help_text="1 from_currency = rate to_currency")
    effective_date = models.DateField()
    notes = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_currency", "to_currency", "effective_date"],
                name="uniq_exchange_rate",
            )
        ]

    def __str__(self):
        return f"1 {self.from_currency_id} = {self.rate} {self.to_currency_id} on {self.effective_date}"


class Buyer(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True, default="")
    contact_phone = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    payment_terms = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(SoftDeleteModel):
    TYPE_CHOICES = [
        ("fabric", "Fabric"),
        ("trims", "Trims & Accessories"),
        ("services", "Services"),
        ("packaging", "Packaging"),
        ("general", "General"),
    ]

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="general")
    contact_person = models.CharField(max_length=150, blank=True, default="")
    contact_phone = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    payment_terms = models.CharField(max_length=200, blank=True, default="")
    ntn = models.CharField(max_length=32, blank=True, default="")
    gst = models.CharField(max_length=32, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ItemCategory(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UnitOfMeasure(SoftDeleteModel):
    DIMENSION_CHOICES = [
        ("count", "Count"),
        ("length", "Length"),
        ("weight", "Weight"),
        ("volume", "Volume"),
        ("area", "Area"),
        ("other", "Other"),
    ]

    code = models.CharField(max_length=16, unique=True)  # PCS, MTR, KG …
    name = models.CharField(max_length=100)
    dimension = models.CharField(max_length=16, choices=DIMENSION_CHOICES, default="count")
    is_base = models.BooleanField(default=False, help_text="Base unit of its dimension")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class UomConversion(SoftDeleteModel):
    from_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="+")
    to_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="+")
    factor = models.DecimalField(max_digits=18, decimal_places=6, help_text="1 from_uom = factor to_uom")

    class Meta:
        ordering = ["from_uom_id"]
        constraints = [
            models.UniqueConstraint(fields=["from_uom", "to_uom"], name="uniq_uom_conversion")
        ]

    def __str__(self):
        return f"{self.from_uom_id} → {self.to_uom_id} × {self.factor}"


class Color(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    hex = models.CharField(max_length=9, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Size(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class SizeGroup(SoftDeleteModel):
    name = models.CharField(max_length=100, unique=True)
    sizes = models.ManyToManyField(Size, through="SizeGroupSize", related_name="groups")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SizeGroupSize(models.Model):
    size_group = models.ForeignKey(SizeGroup, on_delete=models.CASCADE, related_name="group_sizes")
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name="+")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(fields=["size_group", "size"], name="uniq_size_group_size")
        ]


class Warehouse(SoftDeleteModel):
    TYPE_CHOICES = [
        ("fabric_store", "Fabric Store"),
        ("trims_store", "Trims Store"),
        ("general_store", "General Store"),
        ("finished_goods_store", "Finished Goods Store"),
        ("raw_material_store", "Raw Material Store"),
        ("other", "Other"),
    ]

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, default="other")
    location = models.CharField(max_length=150, blank=True, default="")
    address = models.TextField(blank=True, default="")
    manager = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_warehouses"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(ItemCategory, on_delete=models.PROTECT, related_name="items")
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="items")
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    purchase_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    sale_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    reorder_level = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["category"]), models.Index(fields=["unit"])]

    def __str__(self):
        return self.name