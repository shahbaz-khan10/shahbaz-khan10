from django.conf import settings
from django.db import models

from common.base import SoftDeleteModel


class Service(models.Model):
    """A factory module (ams today; mms/pms/stores/... register later)."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.name})"


class Permission(models.Model):
    ACTION_CHOICES = [
        ("view", "View"),
        ("create", "Create"),
        ("edit", "Edit"),
        ("delete", "Delete"),
        ("approve", "Approve"),
    ]

    module = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="permissions")
    entity = models.CharField(max_length=64)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    codename = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=160)

    class Meta:
        ordering = ["codename"]
        constraints = [
            models.UniqueConstraint(fields=["module", "entity", "action"], name="uniq_permission_key")
        ]

    def __str__(self):
        return self.codename


class Role(SoftDeleteModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False, help_text="System roles ship with the seed and are never hard-deleted."
    )
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uniq_role_permission")
        ]


class EmployeeRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-granted_at"]
        constraints = [models.UniqueConstraint(fields=["user", "role"], name="uniq_user_role")]