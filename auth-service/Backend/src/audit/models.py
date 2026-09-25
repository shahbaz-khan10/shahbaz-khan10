from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("approve", "Approve"),
        ("password_change", "Password Change"),
        ("password_reset", "Password Reset"),
    ]

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=24, choices=ACTION_CHOICES, db_index=True)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=64, db_index=True)
    entity_label = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor_user", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id} @ {self.created_at:%Y-%m-%d %H:%M}"


def record(action, entity_type, entity_id, entity_label="", actor=None, ip=None, notes=""):
    AuditLog.objects.create(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id)[:64],
        entity_label=entity_label[:255],
        actor_user=actor,
        ip_address=ip,
        notes=notes[:2000],
    )