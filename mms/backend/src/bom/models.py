from django.db import models

from common.base import SoftDeleteModel


class Bom(SoftDeleteModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
    ]

    style_id = models.PositiveBigIntegerField()
    style_no = models.CharField(max_length=32)
    style_name = models.CharField(max_length=200, blank=True, default="")
    version_no = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    approved_by = models.PositiveBigIntegerField(null=True, blank=True)
    approved_by_name = models.CharField(max_length=200, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["style_id", "version_no"], name="uniq_bom_version")]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["style_id"])]

    def __str__(self):
        return f"{self.style_no} v{self.version_no}"

    @property
    def is_locked(self):
        return self.status == "approved"


class BomItem(models.Model):
    bom = models.ForeignKey(Bom, on_delete=models.CASCADE, related_name="items")
    item_id = models.PositiveBigIntegerField()
    item_code = models.CharField(max_length=32, blank=True, default="")
    item_name = models.CharField(max_length=200)
    item_unit_code = models.CharField(max_length=16, blank=True, default="")
    uom_code = models.CharField(max_length=16, blank=True, default="")
    color_id = models.PositiveBigIntegerField(null=True, blank=True, help_text="blank = all colors")
    color_code = models.CharField(max_length=32, blank=True, default="")
    color_name = models.CharField(max_length=100, blank=True, default="")
    size_id = models.PositiveBigIntegerField(null=True, blank=True, help_text="blank = all sizes")
    size_code = models.CharField(max_length=32, blank=True, default="")
    size_name = models.CharField(max_length=100, blank=True, default="")
    consumption = models.DecimalField(max_digits=14, decimal_places=4, help_text="consumption per piece")
    wastage_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    supplier_id = models.PositiveBigIntegerField(null=True, blank=True)
    supplier_name = models.CharField(max_length=200, blank=True, default="")
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4, default=0, help_text="optional")
    remark = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["bom", "item_id"])]

    def __str__(self):
        return f"{self.item_name} × {self.consumption}"