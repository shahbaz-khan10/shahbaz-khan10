from decimal import Decimal
from typing import Optional

from django.db import models
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel, Field

from common.ams_client import ams
from common.audit import record
from common.auth import AuthBearer, actor, request_token, require_permission
from styles.models import Style

from .models import Bom, BomItem

router = Router(tags=["bom"])


def bom_dict(o: Bom) -> dict:
    return {
        "id": o.id,
        "style_id": o.style_id,
        "style_no": o.style_no,
        "style_name": o.style_name,
        "version_no": o.version_no,
        "status": o.status,
        "is_locked": o.is_locked,
        "approved_by_name": o.approved_by_name,
        "approved_at": o.approved_at.isoformat() if o.approved_at else None,
        "notes": o.notes,
        "item_count": o.items.count(),
    }


def item_dict(i: BomItem) -> dict:
    return {
        "id": i.id,
        "bom_id": i.bom_id,
        "item_id": i.item_id,
        "item_code": i.item_code,
        "item_name": i.item_name,
        "item_unit_code": i.item_unit_code or i.uom_code,
        "color_id": i.color_id,
        "color_code": i.color_code,
        "color_name": i.color_name,
        "size_id": i.size_id,
        "size_code": i.size_code,
        "size_name": i.size_name,
        "consumption": str(i.consumption),
        "wastage_pct": str(i.wastage_pct),
        "uom_code": i.uom_code,
        "supplier_id": i.supplier_id,
        "supplier_name": i.supplier_name,
        "unit_cost": str(i.unit_cost),
    }


class BomCreateIn(BaseModel):
    style_id: int
    notes: str = ""


class BomUpdateIn(BaseModel):
    notes: Optional[str] = None


class BomItemIn(BaseModel):
    item_id: int
    color_id: Optional[int] = None
    size_id: Optional[int] = None
    consumption: Decimal = Field(gt=0)
    wastage_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    supplier_id: Optional[int] = None
    unit_cost: Decimal = Decimal("0")
    remark: str = ""


class BomItemUpdate(BomItemIn):
    pass


def _resolve_item(request, item_id: int):
    item = ams.item(item_id, request_token(request))
    if not item:
        raise HttpError(400, f"Item id {item_id} does not exist in AMS.")
    return item


def _resolve_optional_color(request, color_id):
    if not color_id:
        return {}
    color = ams.color(color_id, request_token(request))
    if not color:
        raise HttpError(400, f"Color id {color_id} does not exist in AMS.")
    return {"color_id": color["id"], "color_code": color.get("code", ""), "color_name": color.get("name", "")}


def _resolve_optional_size(request, size_id):
    if not size_id:
        return {}
    size = ams.size(size_id, request_token(request))
    if not size:
        raise HttpError(400, f"Size id {size_id} does not exist in AMS.")
    return {"size_id": size["id"], "size_code": size.get("code", ""), "size_name": size.get("name", "")}


def _resolve_optional_supplier(request, supplier_id):
    if not supplier_id:
        return {"supplier_id": None, "supplier_name": ""}
    sup = ams.supplier(supplier_id, request_token(request))
    if not sup:
        raise HttpError(400, f"Supplier id {supplier_id} does not exist in AMS.")
    return {"supplier_id": sup["id"], "supplier_name": sup.get("name", "")}


def _guard_locked(bom: Bom):
    if bom.is_locked:
        raise HttpError(400, "Approved BOM is locked. Create a new version to change it.")


def _create_item(request, bom: Bom, payload: BomItemIn):
    item = _resolve_item(request, payload.item_id)
    values = {
        "bom": bom,
        "item_id": item["id"],
        "item_code": item.get("code", ""),
        "item_name": item.get("name", ""),
        "item_unit_code": item.get("unit_code", ""),
        "uom_code": item.get("unit_code", ""),
        "consumption": payload.consumption,
        "wastage_pct": payload.wastage_pct,
        "unit_cost": payload.unit_cost,
        "remark": payload.remark,
    }
    values.update(_resolve_optional_color(request, payload.color_id))
    values.update(_resolve_optional_size(request, payload.size_id))
    values.update(_resolve_optional_supplier(request, payload.supplier_id))
    return BomItem.objects.create(**values)


@router.get("", auth=AuthBearer())
@require_permission("mms.bom.view")
def list_boms(request, style_id: Optional[int] = None, status: str = "", search: str = "", page: int = 1, page_size: int = 20):
    qs = Bom.objects.all()
    if style_id:
        qs = qs.filter(style_id=style_id)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(style_no__icontains=search)
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [bom_dict(o) for o in qs.order_by("-id")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.get("/{pk}", auth=AuthBearer())
@require_permission("mms.bom.view")
def get_bom(request, pk: int):
    try:
        bom = Bom.objects.get(pk=pk)
    except Bom.DoesNotExist:
        raise HttpError(404, "BOM not found.")
    data = bom_dict(bom)
    data["items"] = [item_dict(i) for i in bom.items.all()]
    data["style"] = {"id": bom.style_id, "style_no": bom.style_no}
    return data


@router.post("", auth=AuthBearer())
@require_permission("mms.bom.create")
def create_bom(request, payload: BomCreateIn):
    style_obj = Style.objects.filter(pk=payload.style_id).first()
    if style_obj is None:
        raise HttpError(400, f"Style id {payload.style_id} does not exist.")
    max_ver = Bom.objects.filter(style_id=style_obj.id).aggregate(m=models.Max("version_no"))["m"] or 0
    bom = Bom.objects.create(
        style_id=style_obj.id, style_no=style_obj.style_no, style_name=style_obj.description,
        version_no=max_ver + 1, status="draft", notes=payload.notes,
        created_by=actor(request).get("id"), created_by_name=actor(request).get("full_name"),
    )
    record("create", "bom.bom", bom.pk, str(bom), token=request_token(request))
    return bom_dict(bom)


@router.patch("/{pk}", auth=AuthBearer())
@require_permission("mms.bom.edit")
def update_bom(request, pk: int, payload: BomUpdateIn):
    try:
        bom = Bom.objects.get(pk=pk)
    except Bom.DoesNotExist:
        raise HttpError(404, "BOM not found.")
    _guard_locked(bom)
    if payload.notes is not None:
        bom.notes = payload.notes
        bom.save(update_fields=["notes", "updated_at"])
        record("update", "bom.bom", bom.pk, str(bom), token=request_token(request))
    return bom_dict(bom)


@router.delete("/{pk}", auth=AuthBearer())
@require_permission("mms.bom.delete")
def delete_bom(request, pk: int):
    try:
        bom = Bom.objects.get(pk=pk)
    except Bom.DoesNotExist:
        raise HttpError(404, "BOM not found.")
    if bom.is_locked:
        raise HttpError(400, "Approved BOM cannot be deleted.")
    bom.soft_delete(user=actor(request))
    record("delete", "bom.bom", bom.pk, str(bom), token=request_token(request))
    return {"detail": "BOM deleted."}


# ---------------------------------------------------------------- items
@router.post("/{pk}/items", auth=AuthBearer())
@require_permission("mms.bom.edit")
def add_bom_item(request, pk: int, payload: BomItemIn):
    bom = Bom.objects.filter(pk=pk).first()
    if bom is None:
        raise HttpError(404, "BOM not found.")
    _guard_locked(bom)
    if BomItem.objects.filter(bom=bom, item_id=payload.item_id,
                              color_id=payload.color_id, size_id=payload.size_id).exists():
        raise HttpError(400, "This item/color/size combination already exists in the BOM.")
    item = _create_item(request, bom, payload)
    record("update", "bom.bom", bom.pk, str(bom), token=request_token(request), notes=f"added {item.item_name}")
    return item_dict(item)


@router.patch("/{pk}/items/{item_id}", auth=AuthBearer())
@require_permission("mms.bom.edit")
def update_bom_item(request, pk: int, item_id: int, payload: BomItemUpdate):
    bom = Bom.objects.filter(pk=pk).first()
    if bom is None:
        raise HttpError(404, "BOM not found.")
    _guard_locked(bom)
    item = BomItem.objects.filter(pk=item_id, bom=bom).first()
    if item is None:
        raise HttpError(404, "BOM item not found.")
    data = payload.model_dump(exclude_unset=True)
    if "item_id" in data and data["item_id"] != item.item_id:
        resolved = _resolve_item(request, data["item_id"])
        item.item_id = resolved["id"]
        item.item_code = resolved.get("code", "")
        item.item_name = resolved.get("name", "")
        item.item_unit_code = resolved.get("unit_code", "")
        item.uom_code = resolved.get("unit_code", "")
    if "consumption" in data:
        item.consumption = data["consumption"]
    if "wastage_pct" in data:
        item.wastage_pct = data["wastage_pct"]
    if "unit_cost" in data:
        item.unit_cost = data["unit_cost"]
    if "remark" in data:
        item.remark = data["remark"]
    if "color_id" in data:
        values = _resolve_optional_color(request, data["color_id"])
        item.color_id = values.get("color_id")
        item.color_code = values.get("color_code", "")
        item.color_name = values.get("color_name", "")
    if "size_id" in data:
        values = _resolve_optional_size(request, data["size_id"])
        item.size_id = values.get("size_id")
        item.size_code = values.get("size_code", "")
        item.size_name = values.get("size_name", "")
    if "supplier_id" in data:
        values = _resolve_optional_supplier(request, data["supplier_id"])
        item.supplier_id = values.get("supplier_id")
        item.supplier_name = values.get("supplier_name", "")
    item.save()
    record("update", "bom.bom", bom.pk, str(bom), token=request_token(request), notes=f"updated {item.item_name}")
    return item_dict(item)


@router.delete("/{pk}/items/{item_id}", auth=AuthBearer())
@require_permission("mms.bom.edit")
def delete_bom_item(request, pk: int, item_id: int):
    bom = Bom.objects.filter(pk=pk).first()
    if bom is None:
        raise HttpError(404, "BOM not found.")
    _guard_locked(bom)
    item = BomItem.objects.filter(pk=item_id, bom=bom).first()
    if item is None:
        raise HttpError(404, "BOM item not found.")
    item.delete()
    record("update", "bom.bom", bom.pk, str(bom), token=request_token(request), notes=f"removed {item.item_name}")
    return {"detail": "BOM item removed."}


# ---------------------------------------------------------------- workflow
@router.post("/{pk}/submit", auth=AuthBearer())
@require_permission("mms.bom.edit")
def submit_bom(request, pk: int):
    try:
        bom = Bom.objects.get(pk=pk)
    except Bom.DoesNotExist:
        raise HttpError(404, "BOM not found.")
    if bom.status != "draft":
        raise HttpError(400, "Only draft BOMs can be submitted.")
    bom.status = "submitted"
    bom.save(update_fields=["status", "updated_at"])
    record("update", "bom.bom", bom.pk, str(bom), token=request_token(request), notes="BOM submitted")
    return bom_dict(bom)


@router.post("/{pk}/approve", auth=AuthBearer())
@require_permission("mms.bom.approve")
def approve_bom(request, pk: int):
    try:
        bom = Bom.objects.get(pk=pk)
    except Bom.DoesNotExist:
        raise HttpError(404, "BOM not found.")
    if bom.status != "submitted":
        raise HttpError(400, "Only submitted BOMs can be approved.")
    bom.status = "approved"
    bom.approved_by = actor(request).get("id")
    bom.approved_by_name = actor(request).get("full_name")
    bom.approved_at = timezone.now()
    bom.save(update_fields=["status", "approved_by", "approved_by_name", "approved_at", "updated_at"])
    record("approve", "bom.bom", bom.pk, str(bom), token=request_token(request))
    return bom_dict(bom)


@router.post("/{pk}/new-version", auth=AuthBearer())
@require_permission("mms.bom.create")
def new_bom_version(request, pk: int):
    try:
        source = Bom.objects.select_related().get(pk=pk)
    except Bom.DoesNotExist:
        raise HttpError(404, "BOM not found.")
    max_ver = Bom.objects.filter(style_id=source.style_id).aggregate(m=models.Max("version_no"))["m"] or 0
    copy = Bom.objects.create(
        style_id=source.style_id, style_no=source.style_no, style_name=source.style_name,
        version_no=max_ver + 1, status="draft", notes=source.notes,
        created_by=actor(request).get("id"), created_by_name=actor(request).get("full_name"),
    )
    for old_item in source.items.all():
        BomItem.objects.create(
            bom=copy,
            item_id=old_item.item_id, item_code=old_item.item_code, item_name=old_item.item_name,
            item_unit_code=old_item.item_unit_code, uom_code=old_item.uom_code,
            color_id=old_item.color_id, color_code=old_item.color_code, color_name=old_item.color_name,
            size_id=old_item.size_id, size_code=old_item.size_code, size_name=old_item.size_name,
            consumption=old_item.consumption, wastage_pct=old_item.wastage_pct,
            supplier_id=old_item.supplier_id, supplier_name=old_item.supplier_name,
            unit_cost=old_item.unit_cost, remark=old_item.remark,
        )
    record("create", "bom.bom", copy.pk, str(copy), token=request_token(request), notes="new version from approved BOM")
    return bom_dict(copy)