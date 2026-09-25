import re
from datetime import date
from typing import Optional

from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from ninja.files import UploadedFile
from pydantic import BaseModel

from common.audit import record
from common.auth import AuthBearer, actor, request_token, require_permission
from styles.models import Style

from .models import SampleAttachment, SampleLog, SampleRequest

router = Router(tags=["samples"])


def _next_sample_no() -> str:
    year = timezone.localdate().year
    prefix = f"SPL-{year}-"
    max_seq = 0
    for value in SampleRequest.objects.all_objects().values_list("sample_no", flat=True):
        match = re.match(rf"^{prefix}(\d+)$", value)
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return f"{prefix}{max_seq + 1:04d}"


class SampleCreateIn(BaseModel):
    style_id: int
    sample_type: str = "proto"
    quantity: int = 1
    due_date: Optional[date] = None
    buyer_comments: str = ""


class SampleUpdateIn(BaseModel):
    sample_type: Optional[str] = None
    quantity: Optional[int] = None
    due_date: Optional[date] = None
    sent_date: Optional[date] = None
    buyer_comments: Optional[str] = None


class SampleStatusIn(BaseModel):
    status: str
    comment: str = ""


class SampleCommentIn(BaseModel):
    message: str


TRANSITIONS = {
    "requested": ("in_progress", "rejected", "cancelled"),
    "in_progress": ("sent", "rejected"),
    "sent": ("approved", "rejected", "resubmit"),
    "resubmit": ("in_progress", "rejected"),
    "approved": (),
    "rejected": (),
    "cancelled": (),
}

LABELS = dict(SampleRequest.STATUS_CHOICES)


def sample_dict(s: SampleRequest) -> dict:
    return {
        "id": s.id,
        "sample_no": s.sample_no,
        "style_id": s.style_id,
        "style_no": s.style_no,
        "style_name": s.style_name,
        "sample_type": s.sample_type,
        "quantity": s.quantity,
        "due_date": s.due_date.isoformat() if s.due_date else None,
        "sent_date": s.sent_date.isoformat() if s.sent_date else None,
        "buyer_comments": s.buyer_comments,
        "status": s.status,
        "status_label": LABELS.get(s.status, s.status),
        "is_overdue": s.is_overdue,
        "overdue_days": s.overdue_days(),
        "comment_count": s.logs.count(),
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def sample_detail_dict(s: SampleRequest) -> dict:
    data = sample_dict(s)
    data["logs"] = [
        {
            "id": log.id,
            "message": log.message,
            "status_change_to": log.status_change_to,
            "created_by_name": log.created_by_name,
            "created_at": log.created_at.isoformat(),
        }
        for log in s.logs.all()
    ]
    data["attachments"] = [
        {
            "id": a.id,
            "url": a.file.url,
            "name": a.file.name.rsplit("/", 1)[-1],
            "caption": a.caption,
            "uploaded_by_name": a.uploaded_by_name,
            "uploaded_at": a.uploaded_at.isoformat(),
        }
        for a in s.attachments.all()
    ]
    return data


def _log(request, s: SampleRequest, message: str, status_change_to: str = ""):
    SampleLog.objects.create(
        request=s, message=message, status_change_to=status_change_to,
        created_by=actor(request).get("id"), created_by_name=actor(request).get("full_name"),
    )


@router.get("", auth=AuthBearer())
@require_permission("mms.sample.view")
def list_samples(request, search: str = "", style_id: Optional[int] = None, sample_type: str = "",
                 status: str = "", overdue: Optional[bool] = None,
                 due_from: Optional[date] = None, due_to: Optional[date] = None,
                 page: int = 1, page_size: int = 20):
    from django.db.models import Q

    qs = SampleRequest.objects.all()
    if search:
        qs = qs.filter(Q(sample_no__icontains=search) | Q(style_no__icontains=search))
    if style_id:
        qs = qs.filter(style_id=style_id)
    if sample_type:
        qs = qs.filter(sample_type=sample_type)
    if status:
        qs = qs.filter(status=status)
    if overdue is True:
        qs = qs.filter(status__in=SampleRequest.OPEN_STATUSES, due_date__lt=timezone.localdate())
    if overdue is False:
        from django.db.models import Q as _Q
        qs = qs.exclude(_Q(status__in=SampleRequest.OPEN_STATUSES) & _Q(due_date__lt=timezone.localdate()))
    if due_from:
        qs = qs.filter(due_date__gte=due_from)
    if due_to:
        qs = qs.filter(due_date__lte=due_to)

    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [sample_dict(s) for s in qs.order_by("due_date", "-id")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.get("/{pk}", auth=AuthBearer())
@require_permission("mms.sample.view")
def get_sample(request, pk: int):
    try:
        s = SampleRequest.objects.prefetch_related("logs", "attachments").get(pk=pk)
    except SampleRequest.DoesNotExist:
        raise HttpError(404, "Sample request not found.")
    return sample_detail_dict(s)


@router.post("", auth=AuthBearer())
@require_permission("mms.sample.create")
def create_sample(request, payload: SampleCreateIn):
    style_obj = Style.objects.filter(pk=payload.style_id).first()
    if style_obj is None:
        raise HttpError(400, f"Style id {payload.style_id} does not exist.")
    if payload.sample_type not in dict(SampleRequest.TYPE_CHOICES):
        raise HttpError(400, f"Unknown sample type '{payload.sample_type}'.")
    s = SampleRequest.objects.create(
        sample_no=_next_sample_no(),
        style_id=style_obj.id,
        style_no=style_obj.style_no,
        style_name=style_obj.description,
        sample_type=payload.sample_type,
        quantity=payload.quantity,
        due_date=payload.due_date,
        buyer_comments=payload.buyer_comments,
        status="requested",
        created_by=actor(request).get("id"),
        created_by_name=actor(request).get("full_name"),
    )
    _log(request, s, "Sample requested.")
    record("create", "samples.samplerequest", s.pk, s.sample_no, token=request_token(request))
    return sample_dict(s)


@router.patch("/{pk}", auth=AuthBearer())
@require_permission("mms.sample.edit")
def update_sample(request, pk: int, payload: SampleUpdateIn):
    try:
        s = SampleRequest.objects.get(pk=pk)
    except SampleRequest.DoesNotExist:
        raise HttpError(404, "Sample request not found.")
    if s.status in ("approved", "rejected", "cancelled"):
        raise HttpError(400, f"{s.status.capitalize()} samples cannot be edited.")
    data = payload.model_dump(exclude_unset=True)
    for field in ("sample_type", "quantity", "due_date", "sent_date", "buyer_comments"):
        if field in data:
            setattr(s, field, data[field])
    s.save()
    _log(request, s, "Sample details updated.")
    record("update", "samples.samplerequest", s.pk, s.sample_no, token=request_token(request))
    return sample_dict(s)


@router.post("/{pk}/status", auth=AuthBearer())
@require_permission("mms.sample.edit")
def change_sample_status(request, pk: int, payload: SampleStatusIn):
    try:
        s = SampleRequest.objects.get(pk=pk)
    except SampleRequest.DoesNotExist:
        raise HttpError(404, "Sample request not found.")
    new_status = payload.status
    if new_status == s.status:
        raise HttpError(400, "Sample is already in that status.")
    if new_status not in TRANSITIONS.get(s.status, ()):
        raise HttpError(400, f"Invalid transition {s.status} -> {new_status}.")
    s.status = new_status
    if new_status == "sent" and not s.sent_date:
        s.sent_date = timezone.localdate()
    s.save(update_fields=["status", "sent_date", "updated_at"])
    _log(request, s, payload.comment or f"Status changed to {new_status}.", status_change_to=new_status)
    record("update", "samples.samplerequest", s.pk, s.sample_no, token=request_token(request),
           notes=f"status -> {new_status}")
    return sample_dict(s)


@router.post("/{pk}/comments", auth=AuthBearer())
@require_permission("mms.sample.edit")
def add_sample_comment(request, pk: int, payload: SampleCommentIn):
    s = SampleRequest.objects.filter(pk=pk).first()
    if s is None:
        raise HttpError(404, "Sample request not found.")
    if not payload.message.strip():
        raise HttpError(400, "Comment cannot be empty.")
    _log(request, s, payload.message.strip())
    return sample_detail_dict(SampleRequest.objects.prefetch_related("logs", "attachments").get(pk=s.pk))


@router.post("/{pk}/attachments", auth=AuthBearer())
@require_permission("mms.sample.edit")
def add_sample_attachment(request, pk: int, file: UploadedFile, caption: str = ""):
    s = SampleRequest.objects.filter(pk=pk).first()
    if s is None:
        raise HttpError(404, "Sample request not found.")
    if not file.name:
        raise HttpError(400, "A file is required.")
    a = SampleAttachment.objects.create(
        request=s, file=file, caption=caption,
        uploaded_by=actor(request).get("id"), uploaded_by_name=actor(request).get("full_name"),
    )
    _log(request, s, f"Uploaded attachment: {a.file.name.rsplit('/', 1)[-1]}")
    record("update", "samples.samplerequest", s.pk, s.sample_no, token=request_token(request), notes="attachment uploaded")
    return sample_detail_dict(SampleRequest.objects.prefetch_related("logs", "attachments").get(pk=s.pk))


@router.delete("/{pk}/attachments/{attachment_id}", auth=AuthBearer())
@require_permission("mms.sample.edit")
def delete_sample_attachment(request, pk: int, attachment_id: int):
    a = SampleAttachment.objects.filter(pk=attachment_id, request_id=pk).first()
    if a is None:
        raise HttpError(404, "Attachment not found.")
    name = a.file.name.rsplit("/", 1)[-1]
    a.file.delete(save=False)
    a.delete()
    _log(request, a.request, f"Removed attachment: {name}")
    return {"detail": "Attachment removed."}


@router.delete("/{pk}", auth=AuthBearer())
@require_permission("mms.sample.delete")
def delete_sample(request, pk: int):
    try:
        s = SampleRequest.objects.get(pk=pk)
    except SampleRequest.DoesNotExist:
        raise HttpError(404, "Sample request not found.")
    if s.status in ("approved", "rejected"):
        raise HttpError(400, "Approved or rejected samples cannot be deleted.")
    s.soft_delete(user=actor(request))
    record("delete", "samples.samplerequest", s.pk, s.sample_no, token=request_token(request))
    return {"detail": "Sample request deleted."}