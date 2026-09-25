from django.db import models

from common.base import SoftDeleteModel
from common.files import media_upload_to


class Style(SoftDeleteModel):
    CATEGORY_CHOICES = [
        ("shirt", "Shirt"),
        ("trouser", "Trouser"),
        ("t-shirt", "T-Shirt"),
        ("jacket", "Jacket"),
        ("shorts", "Shorts"),
        ("polo", "Polo"),
        ("kids", "Kids"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("sample_approved", "Sample Approved"),
        ("in_production", "In Production"),
        ("discontinued", "Discontinued"),
    ]

    style_no = models.CharField(max_length=32, unique=True)
    buyer_id = models.PositiveBigIntegerField()
    buyer_code = models.CharField(max_length=32, blank=True, default="")
    buyer_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default="other")
    season = models.CharField(max_length=64, blank=True, default="")
    fabric_type = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="draft")
    version_no = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["buyer_id"]), models.Index(fields=["status"])]

    def __str__(self):
        return self.style_no


class StyleVersion(models.Model):
    style = models.ForeignKey(Style, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveIntegerField()
    notes = models.TextField(blank=True, default="")
    changed_by = models.PositiveBigIntegerField(null=True, blank=True)
    changed_by_name = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_no"]
        constraints = [models.UniqueConstraint(fields=["style", "version_no"], name="uniq_style_version")]


class StyleImage(models.Model):
    style = models.ForeignKey(Style, on_delete=models.CASCADE, related_name="images")
    image = models.FileField(upload_to=media_upload_to("styles"))
    caption = models.CharField(max_length=200, blank=True, default="")
    uploaded_by = models.PositiveBigIntegerField(null=True, blank=True)
    uploaded_by_name = models.CharField(max_length=200, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]