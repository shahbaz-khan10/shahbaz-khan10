from decimal import Decimal
from typing import Optional

from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel, Field

from common.ams_client import ams
from common.audit import record
from common.auth import AuthBearer, actor, request_token, require_permission
from orders.models import Order
from styles.models import Style

from .models import COMPONENT_CHOICES, Costing, CostingLine

router = Router(tags=["costing"])

COMPONENT_LABELS = dict(COMPONENT_CHOICES)


def costing_dict(o: Costing) -> dict:
    return {
        "id": o.id,
        "style_id": o.style_id,
        "style_no": o.style_no,
        "style_name": o.style_name,
        "order_id": o.order_id,
        "order_no": o.order_no,
        "version_no": o.version_no,
        "currency_id": o.currency_id,
        "currency_code": o.currency_code,
        "exchange_rate": str(o.exchange_rate) if o.exchange_rate else None,
        "margin_pct": str(o.margin_pct),
        "buyer_price": str(o.buyer_price),
        "cost_per_piece": str(o.cost_per_piece),
        "total_cost": str(o.total_cost),
        "fob_price": str(o.fob_price),
        "status": o.status,
        "is_locked": o.is_locked,
        "approved_by_name": o.approved_by_name,
        "approved_at": o.approved_at.isoformat() if o.approved_at else None,
        "notes": o.notes,
        "line_count": o.lines.count(),
    }


def line_dict(i: CostingLine) -> dict:
    return {
        "id": i.id,
        "root_id": i.root_id,
        "component": i.component,
        "component_label": COMPONENT_LABELS.get(i.component, i.component),
        "description": i.description,
        "item_id": i.item_id,
        "item_code": i.item_code,
        "item_name": i.item_name,
        "uom_code": i.uom_code,
        "consumption": str(i.consumption),
        "unit_cost": str(i.unit_cost),
        "amount": str(i.amount),
    }


class CostingCreateIn(BaseModel):
    style_id: int
    order_id: Optional[int] = None
    currency_id: int = 0
    exchange_rate: Optional[Decimal] = None
    margin_pct: Decimal = Decimal("0")
    buyer_price: Decimal = Decimal("0")
    notes: str = ""


class CostingUpdateIn(BaseModel):
    currency_id: Optional[int] = None
    exchange_rate: Optional[Decimal] = None
    margin_pct: Optional[Decimal] = None
    buyer_price: Optional[Decimal] = None
    notes: Optional[str] = None
    order_id: Optional[int] = None


class CostingLineIn(BaseModel):
    component: str
    description: str = ""
    item_id: Optional[int] = None
    consumption: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")


class CostingLineUpdate(CostingLineIn):
    pass


def _guard_locked(costing: Costing):
    if costing.is_locked:
        raise HttpError(400, "Approved costing is locked. Create a new version to change it.")


def _resolve_order(request, order_id):
    if not order_id:
        return {"order_id": None, "order_no": ""}
    order = Order.objects.filter(pk=order_id).first()
    if order is None:
        raise HttpError(400, f"Order id {order_id} does not exist.")
    return {"order_id": order.id, "order_no": order.order_no}


def _resolve_currency(request, currency_id):
    currency = ams.currency(currency_id, request_token(request))
    if not currency:
        raise HttpError(400, f"Currency id {currency_id} does not exist in AMS.")
    return currency


def _resolve_item(request, item_id):
    if not item_id:
        return {"item_id": None, "item_code": "", "item_name": ""}
    item = ams.item(item_id, request_token(request))
    if not item:
        raise HttpError(400, f"Item id {item_id} does not exist in AMS.")
    return {"item_id": item["id"], "item_code": item.get("code", ""), "item_name": item.get("name", "")}


@router.get("", auth=AuthBearer())
@require_permission("mms.costing.view")
def list_costings(request, style_id: Optional[int] = None, order_id: Optional[int] = None,
                  status: str = "", page: int = 1, page_size: int = 20):
    qs = Costing.objects.all()
    if style_id:
        qs = qs.filter(style_id=style_id)
    if order_id:
        qs = qs.filter(order_id=order_id)
    if status:
        qs = qs.filter(status=status)
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [costing_dict(o) for o in qs.order_by("-id")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.get("/{pk}", auth=AuthBearer())
@require_permission("mms.costing.view")
def get_costing(request, pk: int):
    try:
        costing = Costing.objects.get(pk=pk)
    except Costing.DoesNotExist:
        raise HttpError(404, "Costing not found.")
    data = costing_dict(costing)
    data["lines"] = [line_dict(l) for l in costing.lines.all()]
    data["style"] = {"id": costing.style_id, "style_no": costing.style_no}
    data["order"] = {"id": costing.order_id, "order_no": costing.order_no}
    return data


@router.post("", auth=AuthBearer())
@require_permission("mms.costing.create")
def create_costing(request, payload: CostingCreateIn):
    style_obj = Style.objects.filter(pk=payload.style_id).first()
    if style_obj is None:
        raise HttpError(400, f"Style id {payload.style_id} does not exist.")
    if not payload.currency_id:
        raise HttpError(400, "currency_id is required.")

    order_values = _resolve_order(request, payload.order_id)
    currency = _resolve_currency(request, payload.currency_id)

    costing = Costing.objects.create(
        style_id=style_obj.id, style_no=style_obj.style_no, style_name=style_obj.description,
        order_id=order_values["order_id"], order_no=order_values["order_no"],
        version_no=1, currency_id=currency["id"], currency_code=currency.get("code", ""),
        exchange_rate=payload.exchange_rate, margin_pct=payload.margin_pct,
        buyer_price=payload.buyer_price, notes=payload.notes, status="draft",
        created_by=actor(request).get("id"), created_by_name=actor(request).get("full_name"),
    )
    costing.recalc()
    record("create", "costing.costing", costing.pk, str(costing), token=request_token(request))
    return costing_dict(costing)


@router.post("/{style_id}/new-version", auth=AuthBearer())
@require_permission("mms.costing.create")
def new_costing_version(request, style_id: int):
    latest = Costing.objects.filter(style_id=style_id).select_related().last()
    if latest is None:
        raise HttpError(404, "No costing versions exist for this style.")
    style_obj = Style.objects.filter(pk=style_id).first()
    if style_obj is None:
        raise HttpError(400, f"Style id {style_id} does not exist.")

    options = Costing.objects.filter(style_id=style_id).values_list("version_no", flat=True)
    version_no = (max(options) if options else 0) + 1

    copy = Costing.objects.create(
        style_id=style_id, style_no=style_obj.style_no, style_name=style_obj.description,
        order_id=latest.order_id, order_no=latest.order_no,
        version_no=version_no, currency_id=latest.currency_id, currency_code=latest.currency_code,
        exchange_rate=latest.exchange_rate, margin_pct=latest.margin_pct, buyer_price=latest.buyer_price,
        status="draft", notes=latest.notes,
        created_by=actor(request).get("id"), created_by_name=actor(request).get("full_name"),
    )
    for old_line in latest.lines.all():
        CostingLine.objects.create(
            costing=copy, root=old_line, component=old_line.component, description=old_line.description,
            item_id=old_line.item_id, item_code=old_line.item_code, item_name=old_line.item_name,
            uom_code=old_line.uom_code, consumption=old_line.consumption, unit_cost=old_line.unit_cost,
        )
    copy.recalc()
    record("create", "costing.costing", copy.pk, str(copy), token=request_token(request), notes="new version")
    return costing_dict(copy)


@router.patch("/{pk}", auth=AuthBearer())
@require_permission("mms.costing.edit")
def update_costing(request, pk: int, payload: CostingUpdateIn):
    try:
        costing = Costing.objects.get(pk=pk)
    except Costing.DoesNotExist:
        raise HttpError(404, "Costing not found.")
    _guard_locked(costing)

    data = payload.model_dump(exclude_unset=True)
    if "currency_id" in data and data["currency_id"] != costing.currency_id:
        currency = _resolve_currency(request, data["currency_id"])
        costing.currency_id = currency["id"]
        costing.currency_code = currency.get("code", "")
    if "order_id" in data:
        values = _resolve_order(request, data["order_id"])
        costing.order_id = values["order_id"]
        costing.order_no = values["order_no"]
    for field in ("exchange_rate", "margin_pct", "buyer_price", "notes"):
        if field in data:
            setattr(costing, field, data[field])
    costing.recalc()
    record("update", "costing.costing", costing.pk, str(costing), token=request_token(request))
    return costing_dict(costing)


@router.delete("/{pk}", auth=AuthBearer())
@require_permission("mms.costing.delete")
def delete_costing(request, pk: int):
    try:
        costing = Costing.objects.get(pk=pk)
    except Costing.DoesNotExist:
        raise HttpError(404, "Costing not found.")
    _guard_locked(costing)
    costing.soft_delete(user=actor(request))
    record("delete", "costing.costing", costing.pk, str(costing), token=request_token(request))
    return {"detail": "Costing deleted."}


# ---------------------------------------------------------------- lines
@router.post("/{pk}/lines", auth=AuthBearer())
@require_permission("mms.costing.edit")
def add_costing_line(request, pk: int, payload: CostingLineIn):
    costing = Costing.objects.filter(pk=pk).first()
    if costing is None:
        raise HttpError(404, "Costing not found.")
    _guard_locked(costing)
    values = dict(
        costing=costing, component=payload.component,
        description=payload.description, consumption=payload.consumption, unit_cost=payload.unit_cost,
    )
    values.update(_resolve_item(request, payload.item_id))
    line = CostingLine.objects.create(**values)
    line.amount = line.consumption * line.unit_cost
    line.save(update_fields=["amount"])
    costing.recalc()
    record("update", "costing.costing", costing.pk, str(costing), token=request_token(request), notes=f"component {payload.component}")
    return line_dict(line)


@router.patch("/{pk}/lines/{line_id}", auth=AuthBearer())
@require_permission("mms.costing.edit")
def update_costing_line(request, pk: int, line_id: int, payload: CostingLineUpdate):
    costing = Costing.objects.filter(pk=pk).first()
    if costing is None:
        raise HttpError(404, "Costing not found.")
    _guard_locked(costing)
    line = CostingLine.objects.filter(pk=line_id, costing=costing).first()
    if line is None:
        raise HttpError(404, "Costing line not found.")
    data = payload.model_dump(exclude_unset=True)
    for field in ("component", "description", "consumption", "unit_cost"):
        if field in data:
            setattr(line, field, data[field])
    if "item_id" in data and data["item_id"] != line.item_id:
        values = _resolve_item(request, data["item_id"])
        line.item_id = values["item_id"]
        line.item_code = values["item_code"]
        line.item_name = values["item_name"]
    line.amount = line.consumption * line.unit_cost
    line.save()
    costing.recalc()
    record("update", "costing.costing", costing.pk, str(costing), token=request_token(request), notes=f"component {line.component}")
    return line_dict(line)


@router.delete("/{pk}/lines/{line_id}", auth=AuthBearer())
@require_permission("mms.costing.edit")
def delete_costing_line(request, pk: int, line_id: int):
    costing = Costing.objects.filter(pk=pk).first()
    if costing is None:
        raise HttpError(404, "Costing not found.")
    _guard_locked(costing)
    line = CostingLine.objects.filter(pk=line_id, costing=costing).first()
    if line is None:
        raise HttpError(404, "Costing line not found.")
    line.delete()
    costing.recalc()
    record("update", "costing.costing", costing.pk, str(costing), token=request_token(request), notes="line removed")
    return {"detail": "Costing line removed."}


# ---------------------------------------------------------------- workflow
@router.post("/{pk}/submit", auth=AuthBearer())
@require_permission("mms.costing.edit")
def submit_costing(request, pk: int):
    costing = Costing.objects.filter(pk=pk).first()
    if costing is None:
        raise HttpError(404, "Costing not found.")
    if costing.status != "draft":
        raise HttpError(400, "Only draft costings can be submitted.")
    costing.status = "submitted"
    costing.save(update_fields=["status", "updated_at"])
    record("update", "costing.costing", costing.pk, str(costing), token=request_token(request), notes="submitted")
    return costing_dict(costing)


@router.post("/{pk}/approve", auth=AuthBearer())
@require_permission("mms.costing.approve")
def approve_costing(request, pk: int):
    costing = Costing.objects.filter(pk=pk).first()
    if costing is None:
        raise HttpError(404, "Costing not found.")
    if costing.status != "submitted":
        raise HttpError(400, "Only submitted costings can be approved.")
    costing.status = "approved"
    costing.approved_by = actor(request).get("id")
    costing.approved_by_name = actor(request).get("full_name")
    costing.approved_at = timezone.now()
    costing.save(update_fields=["status", "approved_by", "approved_by_name", "approved_at", "updated_at"])
    record("approve", "costing.costing", costing.pk, str(costing), token=request_token(request))
    return costing_dict(costing)