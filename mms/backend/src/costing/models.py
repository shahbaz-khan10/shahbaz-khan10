from django.db import models

from common.base import SoftDeleteModel

COMPONENT_CHOICES = [
    ("fabric", "Fabric"),
    ("trims", "Trims & Packaging"),
    ("cm", "Cut & Make"),
    ("embroidery", "Embroidery"),
    ("print", "Print"),
    ("wash", "Wash"),
    ("overhead", "Overhead"),
    ("commission", "Commission"),
    ("freight", "Freight"),
    ("other", "Other"),
]


class Costing(SoftDeleteModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
    ]

    style_id = models.PositiveBigIntegerField()
    style_no = models.CharField(max_length=32)
    style_name = models.CharField(max_length=200, blank=True, default="")
    order_id = models.PositiveBigIntegerField(null=True, blank=True)
    order_no = models.CharField(max_length=32, blank=True, default="")
    version_no = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    currency_id = models.PositiveBigIntegerField()
    currency_code = models.CharField(max_length=8, blank=True, default="")
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True,
                                        help_text="1 currency = N base, captured at approval")
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    buyer_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True,
                                      help_text="buyer's confirmed unit price, for comparison")
    cost_per_piece = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    fob_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_cost = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    approved_by = models.PositiveBigIntegerField(null=True, blank=True)
    approved_by_name = models.CharField(max_length=200, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["style_id", "order_id", "version_no"], name="uniq_costing_version")]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["style_id"])]

    def __str__(self):
        return f"{self.style_no} v{self.version_no}"

    @property
    def is_locked(self):
        return self.status == "approved"

    def recalc(self):
        cost_per_piece = sum((l.amount or 0) for l in self.lines.all())
        self.cost_per_piece = cost_per_piece
        margin = self.margin_pct or 0
        if margin >= 100:
            self.fob_price = cost_per_piece * (1 + margin / 100)
        elif margin > 0:
            self.fob_price = cost_per_piece / (1 - margin / 100)
        else:
            self.fob_price = cost_per_piece
        if self.order_id:
            from orders.models import Order

            order = Order.objects.filter(pk=self.order_id).first()
            qty = order.total_qty if order else 0
            self.total_cost = cost_per_piece * qty
        else:
            self.total_cost = 0
        self.save(update_fields=["cost_per_piece", "fob_price", "total_cost", "updated_at"])


class CostingLine(models.Model):
    costing = models.ForeignKey(Costing, on_delete=models.CASCADE, related_name="lines")
    root = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="derived_lines",
                             help_text="line this version was copied from")
    component = models.CharField(max_length=24, choices=COMPONENT_CHOICES, default="other")
    description = models.CharField(max_length=200, blank=True, default="")
    item_id = models.PositiveBigIntegerField(null=True, blank=True)
    item_code = models.CharField(max_length=32, blank=True, default="")
    item_name = models.CharField(max_length=200, blank=True, default="")
    uom_code = models.CharField(max_length=16, blank=True, default="")
    consumption = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    amount = models.DecimalField(max_digits=18, decimal_places=4, default=0,
                                 help_text="consumption × unit_cost")
    remark = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.component}: {self.amount}"