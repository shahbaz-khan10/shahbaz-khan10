from django.db import models

from common.base import SoftDeleteModel
from common.files import media_upload_to
from django.utils import timezone


class SampleRequest(SoftDeleteModel):
    TYPE_CHOICES = [
        ("proto", "Proto"),
        ("fit", "Fit"),
        ("size_set", "Size Set"),
        ("pp", "PP"),
        ("top", "TOP"),
        ("salesman", "Salesman"),
    ]
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("in_progress", "In Progress"),
        ("sent", "Sent"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("resubmit", "Resubmit"),
    ]
    OPEN_STATUSES = ("requested", "in_progress", "sent", "resubmit")

    sample_no = models.CharField(max_length=32, unique=True)
    style_id = models.PositiveBigIntegerField()
    style_no = models.CharField(max_length=32)
    style_name = models.CharField(max_length=200, blank=True, default="")
    sample_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="proto")
    quantity = models.PositiveIntegerField(default=1)
    due_date = models.DateField(null=True, blank=True)
    sent_date = models.DateField(null=True, blank=True)
    buyer_comments = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="requested")

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["style_id"]),
        ]

    def __str__(self):
        return f"{self.sample_no} ({self.style_no})"

    @property
    def is_overdue(self):
        return (
            self.status in self.OPEN_STATUSES
            and self.due_date is not None
            and self.due_date < timezone.localdate()
        )

    def overdue_days(self):
        if not self.is_overdue:
            return 0
        return (timezone.localdate() - self.due_date).days


class SampleLog(models.Model):
    request = models.ForeignKey(SampleRequest, on_delete=models.CASCADE, related_name="logs")
    message = models.TextField(blank=True, default="")
    status_change_to = models.CharField(max_length=16, blank=True, default="")
    created_by = models.PositiveBigIntegerField(null=True, blank=True)
    created_by_name = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SampleAttachment(models.Model):
    request = models.ForeignKey(SampleRequest, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=media_upload_to("samples"))
    caption = models.CharField(max_length=200, blank=True, default="")
    uploaded_by = models.PositiveBigIntegerField(null=True, blank=True)
    uploaded_by_name = models.CharField(max_length=200, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]