"""Auto-audit: create/update via post_save, delete via is_deleted toggling or
pre_delete. Attaches the request-time actor + IP from thread-local storage."""

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from .middleware import get_client_ip, get_current_user
from .models import record

# Models we observe for automatic create/update/delete auditing.
AUDITED_MODELS = set()


def register(model=None):
    if model is not None:
        AUDITED_MODELS.add(model)
    return model


_PRE_SAVE = {}


@receiver(pre_save)
def _capture_old_state(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    try:
        old_deleted = old_created_lookup = None
        if instance.pk and sender._meta.get_fields:
            row = sender._meta.default_manager.filter(pk=instance.pk).values("is_deleted").first()
            old_deleted = row["is_deleted"] if row else None
        _PRE_SAVE[(sender._meta.label_lower, instance.pk)] = old_deleted
    except Exception:
        pass


@receiver(post_save)
def _audit_post_save(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    actor = get_current_user()
    ip = get_client_ip()
    key = (sender._meta.label_lower, instance.pk)
    old_deleted = _PRE_SAVE.pop(key, None)

    if not created and old_deleted is False and getattr(instance, "is_deleted", False):
        action = "delete"
    elif not created and old_deleted is True and not getattr(instance, "is_deleted", False):
        action = "create"  # restored soft-deleted row is surfaced as creation
    else:
        action = "create" if created else "update"

    record(
        action=action,
        entity_type=sender._meta.label_lower,
        entity_id=instance.pk,
        entity_label=str(instance),
        actor=actor,
        ip=ip,
    )


@receiver(pre_delete)
def _audit_pre_delete(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    record(
        action="delete",
        entity_type=sender._meta.label_lower,
        entity_id=instance.pk,
        entity_label=str(instance),
        actor=get_current_user(),
        ip=get_client_ip(),
    )


def _import_models_for_audit():
    from django.apps import apps

    desired = {
        "authentication.user",
        "permissions.role",
        "permissions.employeerole",
        "employees.companyprofile",
        "employees.department",
        "employees.designation",
        "employees.productionline",
        "employees.employee",
        "masters.buyer",
        "masters.supplier",
        "masters.itemcategory",
        "masters.item",
        "masters.unitofmeasure",
        "masters.uomconversion",
        "masters.color",
        "masters.size",
        "masters.sizegroup",
        "masters.currency",
        "masters.exchangerate",
        "masters.warehouse",
    }
    for label in desired:
        try:
            register(apps.get_model(label))
        except LookupError:
            continue


_import_models_for_audit()