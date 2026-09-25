import re
from datetime import date
from decimal import Decimal
from typing import Optional

from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel, Field

from common.ams_client import ams
from common.audit import record
from common.auth import AuthBearer, actor, request_token, require_permission
from styles.models import Style

from .models import Order, OrderAmendment, OrderLine, OrderLineSize, recalc_line, recalc_order

router = Router(tags=["orders"])


def _next_order_no() -> str:
    year = timezone.localdate().year
    prefix = f"ORD-{year}-"
    max_seq = 0
    for value in Order.objects.all_objects().values_list("order_no", flat=True):
        match = re.match(rf"^{prefix}(\d+)$", value)
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return f"{prefix}{max_seq + 1:04d}"


# ---------------------------------------------------------------- schemas
class OrderSizeIn(BaseModel):
    size_id: int
    size_code: str = ""
    size_name: str = ""
    quantity: Decimal = Field(ge=0)


class OrderLineIn(BaseModel):
    style_id: int
    color_id: int
    color_code: str = ""
    color_name: str = ""
    unit_price: Decimal = Field(ge=0)
    sizes: list[OrderSizeIn] = []
    remarks: str = ""


class OrderCreateIn(BaseModel):
    buyer_po_no: str = ""
    buyer_id: int
    order_date: date = Field(default_factory=timezone.localdate)
    ship_date: Optional[date] = None
    currency_id: int
    payment_terms: str = ""
    merchandiser_user_id: Optional[int] = None
    excess_allowance_pct: Decimal = Decimal("0")
    short_allowance_pct: Decimal = Decimal("0")
    notes: str = ""
    lines: list[OrderLineIn] = Field(default_factory=list)


class OrderUpdateIn(BaseModel):
    buyer_po_no: Optional[str] = None
    buyer_id: Optional[int] = None
    order_date: Optional[date] = None
    ship_date: Optional[date] = None
    currency_id: Optional[int] = None
    payment_terms: Optional[str] = None
    merchandiser_user_id: Optional[int] = None
    excess_allowance_pct: Optional[Decimal] = None
    short_allowance_pct: Optional[Decimal] = None
    notes: Optional[str] = None
    lines: Optional[list[OrderLineIn]] = None
    amendment_reason: str = ""


class StatusIn(BaseModel):
    status: str
    reason: str = ""


# ---------------------------------------------------------------- ams reference helpers
def _resolve_buyer(request, buyer_id: int):
    buyer = ams.buyer(buyer_id, request_token(request))
    if not buyer:
        raise HttpError(400, f"Buyer id {buyer_id} does not exist in AMS.")
    return buyer


def _resolve_currency(request, currency_id: int):
    currency = ams.currency(currency_id, request_token(request))
    if not currency:
        raise HttpError(400, f"Currency id {currency_id} does not exist in AMS.")
    return currency


def _resolve_color(request, color_id: int):
    color = ams.color(color_id, request_token(request))
    if not color:
        raise HttpError(400, f"Color id {color_id} does not exist in AMS.")
    return color


def _resolve_size(request, size_id: int):
    size = ams.size(size_id, request_token(request))
    if not size:
        raise HttpError(400, f"Size id {size_id} does not exist in AMS.")
    return size


def _resolve_style(style_id: int):
    style_obj = Style.objects.filter(pk=style_id).first()
    if style_obj is None:
        raise HttpError(400, f"Style id {style_id} does not exist.")
    return style_obj


def _resolve_merch(request, user_id: int):
    user = ams.fetch_user(user_id, request_token(request))
    if not user:
        raise HttpError(400, f"Merchandiser user id {user_id} does not exist in AMS.")
    return user.get("full_name") or user.get("username", "")


# ---------------------------------------------------------------- serializers
def line_dict(line: OrderLine) -> dict:
    return {
        "id": line.id,
        "style_id": line.style_id,
        "style_no": line.style_no,
        "style_name": line.style_name,
        "color_id": line.color_id,
        "color_code": line.color_code,
        "color_name": line.color_name,
        "unit_price": str(line.unit_price),
        "quantity": str(line.quantity),
        "total_value": str(line.total_value),
        "remarks": line.remarks,
        "sizes": [
            {
                "id": s.id,
                "size_id": s.size_id,
                "size_code": s.size_code,
                "size_name": s.size_name,
                "quantity": str(s.quantity),
            }
            for s in line.sizes.all()
        ],
    }


def order_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "order_no": o.order_no,
        "buyer_po_no": o.buyer_po_no,
        "buyer_id": o.buyer_id,
        "buyer_code": o.buyer_code,
        "buyer_name": o.buyer_name,
        "order_date": o.order_date.isoformat() if o.order_date else None,
        "ship_date": o.ship_date.isoformat() if o.ship_date else None,
        "currency_id": o.currency_id,
        "currency_code": o.currency_code,
        "payment_terms": o.payment_terms,
        "merchandiser_user_id": o.merchandiser_user_id,
        "merchandiser_name": o.merchandiser_name,
        "excess_allowance_pct": str(o.excess_allowance_pct),
        "short_allowance_pct": str(o.short_allowance_pct),
        "status": o.status,
        "total_qty": str(o.total_qty),
        "total_value": str(o.total_value),
        "notes": o.notes,
        "line_count": o.lines.count(),
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def order_detail_dict(o: Order) -> dict:
    data = order_dict(o)
    data["lines"] = [line_dict(l) for l in o.lines.all()]
    data["amendments"] = [
        {
            "id": a.id,
            "version_no": a.version_no,
            "reason": a.reason,
            "changes": a.changes,
            "changed_by_name": a.changed_by_name,
            "created_at": a.created_at.isoformat(),
        }
        for a in o.amendments.all()
    ]
    return data


def _replace_lines(request, order: Order, lines):
    OrderLine.objects.filter(order=order).delete()
    for line_in in lines:
        style_obj = _resolve_style(line_in.style_id)
        color = _resolve_color(request, line_in.color_id)
        if not line_in.sizes:
            raise HttpError(400, f"Order line for {style_obj.style_no} needs at least one size quantity.")
        line = OrderLine.objects.create(
            order=order,
            style_id=style_obj.id,
            style_no=style_obj.style_no,
            style_name=style_obj.description,
            color_id=color["id"],
            color_code=color.get("code", ""),
            color_name=color.get("name", ""),
            unit_price=line_in.unit_price,
            remarks=line_in.remarks,
        )
        for size_in in line_in.sizes:
            size = _resolve_size(request, size_in.size_id)
            if size_in.quantity <= 0:
                raise HttpError(400, f"Size {size.get('code', '')} quantity must be greater than zero.")
            OrderLineSize.objects.create(
                line=line, size_id=size["id"], size_code=size.get("code", ""),
                size_name=size.get("name", ""), quantity=size_in.quantity,
            )
        recalc_line(line)


def _append_amendment(order: Order, reason: str, changes: dict, request, action="update"):
    version_no = (order.amendments.count() or 0) + 1
    OrderAmendment.objects.create(
        order=order, version_no=version_no, reason=reason[:200], changes=changes,
        changed_by=actor(request).get("id"), changed_by_name=actor(request).get("full_name"),
    )
    record(action, "orders.order", order.pk, order.order_no, token=request_token(request), notes=reason[:2000])


# ---------------------------------------------------------------- endpoints
@router.get("", auth=AuthBearer())
@require_permission("mms.order.view")
def list_orders(request, search: str = "", status: str = "", buyer_id: Optional[int] = None,
                style_id: Optional[int] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
                page: int = 1, page_size: int = 20):
    from django.db.models import Q

    qs = Order.objects.all().order_by("-id")
    if search:
        qs = qs.filter(
            Q(order_no__icontains=search)
            | Q(buyer_po_no__icontains=search)
            | Q(buyer_name__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if buyer_id:
        qs = qs.filter(buyer_id=buyer_id)
    if style_id:
        qs = qs.filter(lines__style_id=style_id).distinct()
    if date_from:
        qs = qs.filter(order_date__gte=date_from)
    if date_to:
        qs = qs.filter(order_date__lte=date_to)

    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [order_dict(o) for o in qs[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.get("/{pk}", auth=AuthBearer())
@require_permission("mms.order.view")
def get_order(request, pk: int):
    try:
        o = Order.objects.prefetch_related("lines__sizes", "amendments").get(pk=pk)
    except Order.DoesNotExist:
        raise HttpError(404, "Order not found.")
    return order_detail_dict(o)


@router.post("", auth=AuthBearer())
@require_permission("mms.order.create")
def create_order(request, payload: OrderCreateIn):
    buyer = _resolve_buyer(request, payload.buyer_id)
    currency = _resolve_currency(request, payload.currency_id)
    if not payload.lines:
        raise HttpError(400, "An order must have at least one line.")
    if payload.ship_date and payload.ship_date < payload.order_date:
        raise HttpError(400, "Ship date cannot be before order date.")

    merch_name = ""
    if payload.merchandiser_user_id:
        merch_name = _resolve_merch(request, payload.merchandiser_user_id)

    order = Order.objects.create(
        order_no=_next_order_no(),
        buyer_po_no=payload.buyer_po_no.strip().upper(),
        buyer_id=buyer["id"],
        buyer_code=buyer.get("code", ""),
        buyer_name=buyer.get("name", ""),
        order_date=payload.order_date,
        ship_date=payload.ship_date,
        currency_id=currency["id"],
        currency_code=currency.get("code", ""),
        payment_terms=payload.payment_terms,
        merchandiser_user_id=payload.merchandiser_user_id,
        merchandiser_name=merch_name,
        excess_allowance_pct=payload.excess_allowance_pct,
        short_allowance_pct=payload.short_allowance_pct,
        notes=payload.notes,
        status="draft",
        created_by=actor(request).get("id"),
        created_by_name=actor(request).get("full_name"),
    )
    _replace_lines(request, order, payload.lines)
    recalc_order(order)
    record("create", "orders.order", order.pk, order.order_no, token=request_token(request))
    return order_detail_dict(Order.objects.prefetch_related("lines__sizes", "amendments").get(pk=order.pk))


@router.patch("/{pk}", auth=AuthBearer())
@require_permission("mms.order.edit")
def update_order(request, pk: int, payload: OrderUpdateIn):
    try:
        order = Order.objects.prefetch_related("lines__sizes").get(pk=pk)
    except Order.DoesNotExist:
        raise HttpError(404, "Order not found.")
    if order.status in ("closed", "shipped"):
        raise HttpError(400, "Shipped or closed orders cannot be edited.")

    data = payload.model_dump(exclude_unset=True)
    changes = {}
    header_fields = ("buyer_po_no", "order_date", "ship_date", "payment_terms",
                     "excess_allowance_pct", "short_allowance_pct", "notes", "merchandiser_user_id")
    for field in header_fields:
        if field in data and data[field] != getattr(order, field):
            changes[field] = {"from": str(getattr(order, field)), "to": str(data[field])}
            setattr(order, field, data[field])
    if "buyer_id" in data and data["buyer_id"] != order.buyer_id:
        buyer = _resolve_buyer(request, data["buyer_id"])
        changes["buyer_id"] = {"from": order.buyer_id, "to": data["buyer_id"]}
        order.buyer_id = buyer["id"]
        order.buyer_code = buyer.get("code", "")
        order.buyer_name = buyer.get("name", "")
    if "currency_id" in data and data["currency_id"] != order.currency_id:
        currency = _resolve_currency(request, data["currency_id"])
        changes["currency_id"] = {"from": order.currency_id, "to": data["currency_id"]}
        order.currency_id = currency["id"]
        order.currency_code = currency.get("code", "")
    if "merchandiser_user_id" in data:
        order.merchandiser_user_id = data["merchandiser_user_id"] or None
        order.merchandiser_name = _resolve_merch(request, order.merchandiser_user_id) if order.merchandiser_user_id else ""

    if "lines" in data:
        _replace_lines(request, order, data["lines"])
        changes["lines"] = {"note": f"Order lines replaced ({len(data['lines'])} lines)."}

    if changes:
        order.save()
        recalc_order(order)
        _append_amendment(order, payload.amendment_reason or "Order edited.", changes, request)

    return order_detail_dict(Order.objects.prefetch_related("lines__sizes", "amendments").get(pk=order.pk))


@router.post("/{pk}/status", auth=AuthBearer())
@require_permission("mms.order.approve")
def change_order_status(request, pk: int, payload: StatusIn):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        raise HttpError(404, "Order not found.")
    new_status = payload.status
    if new_status == order.status:
        raise HttpError(400, "Order is already in that status.")
    allowed = order.TRANSITIONS.get(order.status, ())
    if new_status not in allowed:
        raise HttpError(400, f"Invalid transition {order.status} -> {new_status}.")
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    _append_amendment(order, payload.reason or f"Status changed to {new_status}.",
                      {"status": {"from": "", "to": new_status}}, request,
                      action="approve" if new_status != "cancelled" else "delete")
    return order_dict(order)


@router.delete("/{pk}", auth=AuthBearer())
@require_permission("mms.order.delete")
def delete_order(request, pk: int):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        raise HttpError(404, "Order not found.")
    if order.status not in ("draft", "cancelled"):
        raise HttpError(400, "Only draft or cancelled orders can be deleted.")
    order.soft_delete(user=actor(request))
    record("delete", "orders.order", order.pk, order.order_no, token=request_token(request))
    return {"detail": "Order deleted."}