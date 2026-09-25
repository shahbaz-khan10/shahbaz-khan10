from typing import Optional

from django.db.models import Q
from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel

from authentication.api import AuthBearer
from permissions.decorators import require_permission
from .models import AuditLog, record

router = Router(tags=["audit"])

ACTION_LABELS = dict(AuditLog.ACTION_CHOICES)


class AuditWriteIn(BaseModel):
    action: str
    entity_type: str
    entity_id: str = ""
    entity_label: str = ""
    notes: str = ""


@router.post("/logs", auth=AuthBearer())
@require_permission("ams.audit.create")
def write_audit_log(request, payload: AuditWriteIn):
    """Central audit write used by MMS (and any other service).

    The actor is always taken from the authenticated token — never accepted
    from the client.
    """
    allowed = {"create", "update", "delete", "approve"}
    action = payload.action if payload.action in allowed else "update"
    if not payload.entity_type.strip():
        raise HttpError(400, "entity_type is required.")
    user = request.auth
    record(
        action=action,
        entity_type=payload.entity_type.strip()[:100],
        entity_id=payload.entity_id.strip()[:64],
        entity_label=payload.entity_label.strip()[:255],
        actor=user,
        ip=request.META.get("REMOTE_ADDR"),
        notes=payload.notes[:2000],
    )
    return {"detail": "Logged."}


def audit_dict(o: AuditLog) -> dict:
    return {
        "id": o.id,
        "action": o.action,
        "action_label": ACTION_LABELS.get(o.action, o.action),
        "actor_user_id": o.actor_user_id,
        "actor_username": o.actor_user.username if o.actor_user_id else None,
        "actor_label": o.actor_user.full_name if o.actor_user_id else "System",
        "entity_type": o.entity_type,
        "entity_id": o.entity_id,
        "entity_label": o.entity_label,
        "ip_address": o.ip_address,
        "notes": o.notes,
        "created_at": o.created_at.isoformat(),
    }


@router.get("/logs", auth=AuthBearer())
@require_permission("ams.audit.view")
def list_audit_logs(
    request,
    actor_user_id: Optional[int] = None,
    action: str = "",
    entity_type: str = "",
    entity_id: str = "",
    q: str = "",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 30,
):
    qs = AuditLog.objects.select_related("actor_user").all()
    if actor_user_id:
        qs = qs.filter(actor_user_id=actor_user_id)
    if action:
        qs = qs.filter(action=action)
    if entity_type:
        qs = qs.filter(entity_type__icontains=entity_type)
    if entity_id:
        qs = qs.filter(entity_id__icontains=entity_id)
    if q:
        qs = qs.filter(
            Q(entity_label__icontains=q)
            | Q(notes__icontains=q)
            | Q(actor_user__username__icontains=q)
            | Q(actor_user__employee__full_name__icontains=q)
        )
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [audit_dict(o) for o in qs.order_by("-created_at")[(page - 1) * page_size : page * page_size]]
    return {
        "items": items,
        "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0},
    }