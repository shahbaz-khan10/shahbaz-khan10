"""Shared base models for the MMS service.

Mirrors the AMS convention (created_at/updated_at/created_by + soft delete on
every table). Because MMS has its own database, user references are stored as
AMS user ids plus a denormalized display name instead of a ForeignKey.
"""

from django.db import models


class ActorMixin(models.Model):
    """Denormalized actor reference (AMS user id + name) on a table."""

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.PositiveBigIntegerField(null=True, blank=True, help_text="AMS user id")
    created_by_name = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        for obj in self:
            obj.delete()

    def hard_delete(self):
        return super().delete()

    def restore(self):
        return self.update(is_deleted=False, deleted_at=None, deleted_by=None, deleted_by_name="")

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_objects(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        return self.all_objects().filter(is_deleted=True)


class SoftDeleteModel(TimeStampedModel):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.PositiveBigIntegerField(null=True, blank=True, help_text="AMS user id")
    deleted_by_name = models.CharField(max_length=200, blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user.get("id")
            self.deleted_by_name = user.get("full_name", user.get("username", ""))
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "deleted_by_name", "updated_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deleted_by_name = ""
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "deleted_by_name", "updated_at"])

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()