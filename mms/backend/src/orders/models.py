from django.db import models

from common.base import SoftDeleteModel
from django.utils import timezone


class Order(SoftDeleteModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
        ("in_production", "In Production"),
        ("shipped", "Shipped"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]
    # legal transitions: key -> allowed next statuses
    TRANSITIONS = {
        "draft": ("confirmed", "cancelled"),
        "confirmed": ("in_production", "cancelled"),
        "in_production": ("shipped", "cancelled"),
        "shipped": ("closed",),
        "closed": (),
        "cancelled": (),
    }

    order_no = models.CharField(max_length=32, unique=True)
    buyer_po_no = models.CharField(max_length=100)
    buyer_id = models.PositiveBigIntegerField()
    buyer_code = models.CharField(max_length=32, blank=True, default="")
    buyer_name = models.CharField(max_length=200)
    order_date = models.DateField(default=timezone.localdate)
    ship_date = models.DateField(null=True, blank=True)
    currency_id = models.PositiveBigIntegerField()
    currency_code = models.CharField(max_length=8, blank=True, default="")
    payment_terms = models.CharField(max_length=200, blank=True, default="")
    merchandiser_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    merchandiser_name = models.CharField(max_length=200, blank=True, default="")
    excess_allowance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    short_allowance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="draft")
    total_qty = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_value = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["ship_date"]),
            models.Index(fields=["order_date"]),
            models.Index(fields=["buyer_id"]),
        ]

    def __str__(self):
        return f"{self.order_no} ({self.buyer_name})"

    @property
    def is_open(self):
        return self.status in ("draft", "confirmed", "in_production")


def recalc_line(line: "OrderLine"):
    total_qty = sum((s.quantity or 0) for s in line.sizes.all()) or 0
    line.quantity = total_qty
    line.total_value = (line.quantity or 0) * (line.unit_price or 0)
    line.save(update_fields=["quantity", "total_value"])


def recalc_order(order: Order):
    qty = sum((l.quantity or 0) for l in order.lines.all()) or 0
    value = sum((l.total_value or 0) for l in order.lines.all()) or 0
    order.total_qty = qty
    order.total_value = value
    order.save(update_fields=["total_qty", "total_value", "updated_at"])


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    style_id = models.PositiveBigIntegerField()
    style_no = models.CharField(max_length=32)
    style_name = models.CharField(max_length=200, blank=True, default="")
    color_id = models.PositiveBigIntegerField()
    color_code = models.CharField(max_length=32, blank=True, default="")
    color_name = models.CharField(max_length=100, blank=True, default="")
    unit_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_value = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    remarks = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["order", "style_id", "color_id"], name="uniq_order_line")
        ]

    def __str__(self):
        return f"{self.style_no} {self.color_name}"


class OrderLineSize(models.Model):
    line = models.ForeignKey(OrderLine, on_delete=models.CASCADE, related_name="sizes")
    size_id = models.PositiveBigIntegerField()
    size_code = models.CharField(max_length=32, blank=True, default="")
    size_name = models.CharField(max_length=100, blank=True, default="")
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["line", "size_id"], name="uniq_order_line_size")]

    def __str__(self):
        return f"{self.size_code}: {self.quantity}"


class OrderAmendment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="amendments")
    version_no = models.PositiveIntegerField()
    reason = models.CharField(max_length=200, blank=True, default="")
    changes = models.JSONField(default=dict, blank=True)
    changed_by = models.PositiveBigIntegerField(null=True, blank=True)
    changed_by_name = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_no"]

    def __str__(self):
        return f"{self.order.order_no} amd #{self.version_no}"