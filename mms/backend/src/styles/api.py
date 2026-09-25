import re
from typing import Optional

from ninja import Router
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja import Form
from pydantic import BaseModel

from common.ams_client import ams
from common.audit import record
from common.auth import AuthBearer, actor, actor_values, request_token, require_permission

from .models import Style, StyleVersion, StyleImage

router = Router(tags=["styles"])

SEARCH_FIELDS = ("style_no", "buyer_name", "buyer_code", "description", "season", "fabric_type")


def _next_style_no() -> str:
    max_no = 0
    for value in Style.objects.all_objects().values_list("style_no", flat=True):
        match = re.match(r"^STY-(\d+)$", value)
        if match:
            max_no = max(max_no, int(match.group(1)))
    return f"STY-{max_no + 1:04d}"


def style_dict(o: Style) -> dict:
    return {
        "id": o.id,
        "style_no": o.style_no,
        "buyer_id": o.buyer_id,
        "buyer_code": o.buyer_code,
        "buyer_name": o.buyer_name,
        "description": o.description,
        "category": o.category,
        "season": o.season,
        "fabric_type": o.fabric_type,
        "status": o.status,
        "version_no": o.version_no,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        "image_urls": [{"id": i.id, "url": i.image.url, "caption": i.caption} for i in o.images.all()[:6]],
    }


class StyleIn(BaseModel):
    buyer_id: int
    description: str = ""
    category: str = "other"
    season: str = ""
    fabric_type: str = ""
    status: str = "draft"


class StyleUpdate(BaseModel):
    buyer_id: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    season: Optional[str] = None
    fabric_type: Optional[str] = None
    status: Optional[str] = None
    version_notes: str = ""


@router.get("", auth=AuthBearer())
@require_permission("mms.style.view")
def list_styles(request, search: str = "", buyer_id: Optional[int] = None, status: str = "", page: int = 1, page_size: int = 20):
    from django.db.models import Q

    qs = Style.objects.prefetch_related("images").all()
    if search:
        q = Q()
        for field in SEARCH_FIELDS:
            q |= Q(**{f"{field}__icontains": search})
        qs = qs.filter(q)
    if buyer_id:
        qs = qs.filter(buyer_id=buyer_id)
    if status:
        qs = qs.filter(status=status)
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [style_dict(o) for o in qs.order_by("-id")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.get("/{pk}", auth=AuthBearer())
@require_permission("mms.style.view")
def get_style(request, pk: int):
    try:
        return style_dict(Style.objects.prefetch_related("images").get(pk=pk))
    except Style.DoesNotExist:
        raise HttpError(404, "Style not found.")


@router.post("", auth=AuthBearer())
@require_permission("mms.style.create")
def create_style(request, payload: StyleIn):
    buyer = ams.buyer(payload.buyer_id, request_token(request))
    if not buyer:
        raise HttpError(400, f"Buyer id {payload.buyer_id} does not exist in AMS.")
    if payload.category not in dict(Style.CATEGORY_CHOICES):
        raise HttpError(400, "Invalid style category.")
    if payload.status not in dict(Style.STATUS_CHOICES):
        raise HttpError(400, "Invalid style status.")
    data = payload.model_dump(exclude_unset=True)
    data.update(
        {
            "style_no": _next_style_no(),
            "buyer_code": buyer.get("code", ""),
            "buyer_name": buyer.get("name", ""),
            "version_no": 1,
        }
    )
    data.update(actor_values(request))
    obj = Style.objects.create(**data)
    record("create", "styles.style", obj.pk, obj.style_no, token=request_token(request))
    return style_dict(obj)


@router.patch("/{pk}", auth=AuthBearer())
@require_permission("mms.style.edit")
def update_style(request, pk: int, payload: StyleUpdate):
    try:
        obj = Style.objects.get(pk=pk)
    except Style.DoesNotExist:
        raise HttpError(404, "Style not found.")
    data = payload.model_dump(exclude_unset=True)
    version_notes = payload.version_notes or "Updated details."
    changed = False
    if "buyer_id" in data and data["buyer_id"] != obj.buyer_id:
        buyer = ams.buyer(data["buyer_id"], request_token(request))
        if not buyer:
            raise HttpError(400, f"Buyer id {data['buyer_id']} does not exist in AMS.")
        obj.buyer_id = data["buyer_id"]
        obj.buyer_code = buyer.get("code", "")
        obj.buyer_name = buyer.get("name", "")
        changed = True
    for field in ("description", "category", "season", "fabric_type", "status"):
        if field in data and data[field] != getattr(obj, field):
            if field in ("category", "status"):
                choices = dict(Style.CATEGORY_CHOICES if field == "category" else Style.STATUS_CHOICES)
                if data[field] not in choices:
                    raise HttpError(400, f"Invalid {field}.")
            setattr(obj, field, data[field])
            changed = True
    if changed:
        obj.version_no += 1
        StyleVersion.objects.create(
            style=obj, version_no=obj.version_no, notes=version_notes,
            changed_by=actor(request).get("id"), changed_by_name=actor(request).get("full_name"),
        )
    obj.save()
    record("update", "styles.style", obj.pk, obj.style_no, token=request_token(request), notes=version_notes)
    return style_dict(obj)


@router.delete("/{pk}", auth=AuthBearer())
@require_permission("mms.style.delete")
def delete_style(request, pk: int):
    try:
        obj = Style.objects.get(pk=pk)
    except Style.DoesNotExist:
        raise HttpError(404, "Style not found.")
    from orders.models import OrderLine

    if OrderLine.objects.filter(style_id=obj.id).exists():
        raise HttpError(400, "Cannot delete a style that is used by buyer orders.")
    obj.soft_delete(user=actor(request))
    record("delete", "styles.style", obj.pk, obj.style_no, token=request_token(request))
    return {"detail": "Style deleted."}


@router.get("/{pk}/versions", auth=AuthBearer())
@require_permission("mms.style.view")
def style_versions(request, pk: int):
    Style.objects.get(pk=pk)
    return [
        {
            "id": v.id,
            "version_no": v.version_no,
            "notes": v.notes,
            "changed_by_name": v.changed_by_name,
            "created_at": v.created_at.isoformat(),
        }
        for v in StyleVersion.objects.filter(style_id=pk)
    ]


@router.post("/{pk}/images", auth=AuthBearer())
@require_permission("mms.style.edit")
def upload_style_image(request, pk: int, image: UploadedFile, caption: str = Form("")):
    try:
        style_obj = Style.objects.get(pk=pk)
    except Style.DoesNotExist:
        raise HttpError(404, "Style not found.")
    img = StyleImage.objects.create(
        style=style_obj,
        image=image,
        caption=caption,
        uploaded_by=actor(request).get("id"),
        uploaded_by_name=actor(request).get("full_name"),
    )
    return {"id": img.id, "url": img.image.url, "caption": img.caption}


@router.delete("/{pk}/images/{image_id}", auth=AuthBearer())
@require_permission("mms.style.edit")
def delete_style_image(request, pk: int, image_id: int):
    img = StyleImage.objects.filter(pk=image_id, style_id=pk).first()
    if img is None:
        raise HttpError(404, "Image not found.")
    img.image.delete(save=False)
    img.delete()
    return {"detail": "Image removed."}