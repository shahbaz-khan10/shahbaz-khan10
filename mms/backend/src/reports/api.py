"""Reports and dashboard for MMS. All endpoints are read-only; CSV=full export,
HTML=JSON for the UI. Reports are gated by `mms.report.view`, the dashboard by
`mms.dashboard.view`.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Count, Sum, Q as DJQ
from ninja import Router

from common.auth import AuthBearer, require_permission
from common.csv_export import csv_response
from bom.models import Bom
from bom.services import material_requirement
from costing.models import Costing
from orders.models import Order
from samples.models import SampleRequest
from styles.models import Style

router = Router(tags=["reports"])


def _maybe_csv(request, filename: str, column_names, rows):
    fmt = request.GET.get("format", "json")
    if fmt == "csv":
        return csv_response(filename, column_names, rows)
    return {"items": rows, "total": len(rows)}


def _orders_rows() -> list[dict]:
    rows = []
    for o in Order.objects.select_related().all().order_by("ship_date"):
        style_no = ""
        qty = o.total_qty
        lines = list(o.lines.all())
        if lines:
            style_no = "; ".join(dict.fromkeys(l.style_no for l in lines))
            # total qty is already aggregated on the order
        rows.append({
            "order_no": o.order_no,
            "buyer_po_no": o.buyer_po_no,
            "buyer_name": o.buyer_name,
            "styles": style_no,
            "order_date": o.order_date.isoformat() if o.order_date else "",
            "ship_date": o.ship_date.isoformat() if o.ship_date else "",
            "status": o.status,
            "currency_code": o.currency_code,
            "total_qty": str(o.total_qty),
            "total_value": str(o.total_value),
        })
    return rows


@router.get("/orders", auth=AuthBearer())
@require_permission("mms.report.view")
def orders_report(request, status: str = ""):
    rows = _orders_rows()
    if status:
        rows = [r for r in rows if r["status"] == status]
    return _maybe_csv(request, "orders",
                      ["order_no", "buyer_po_no", "buyer_name", "styles", "order_date",
                       "ship_date", "status", "currency_code", "total_qty", "total_value"], rows)


@router.get("/orders/{order_id}/material-requirement", auth=AuthBearer())
@require_permission("mms.report.view")
def order_material_requirement(request, order_id: int):
    order = Order.objects.filter(pk=order_id).first()
    if order is None:
        from ninja.errors import HttpError

        raise HttpError(404, "Order not found.")
    result = material_requirement(order)
    if request.GET.get("format") == "csv":
        columns = ["style_no", "item_code", "item_name", "uom_code", "color_code", "size_code",
                   "requirement", "unit_cost", "total_cost"]
        rows = [
            {
                "style_no": it["style_no"], "item_code": it["item_code"], "item_name": it["item_name"],
                "uom_code": it["uom_code"], "color_code": it["color_code"], "size_code": it["size_code"],
                "requirement": str(it["requirement"]), "unit_cost": str(it["unit_cost"]),
                "total_cost": str(it["total_cost"]),
            }
            for it in result["items"]
        ]
        from common.csv_export import csv_response

        return csv_response(f"material-requirement-{order.order_no}", columns, rows)
    return result


@router.get("/material-requirement", auth=AuthBearer())
@require_permission("mms.report.view")
def material_requirement_report(request):
    from django.db.models import Q as _Q

    rows = []
    orders = Order.objects.filter(status__in=("confirmed", "in_production")).order_by("ship_date")
    for order in orders:
        result = material_requirement(order)
        for it in result["items"]:
            rows.append({
                "order_no": order.order_no,
                "style_no": it["style_no"],
                "item_code": it["item_code"],
                "item_name": it["item_name"],
                "uom_code": it["uom_code"],
                "color_code": it["color_code"],
                "size_code": it["size_code"],
                "requirement": str(it["requirement"]),
                "unit_cost": str(it["unit_cost"]),
                "total_cost": str(it["total_cost"]),
                "ship_date": order.ship_date.isoformat() if order.ship_date else "",
            })
    return _maybe_csv(request, "material-requirements",
                      ["order_no", "style_no", "item_code", "item_name", "uom_code", "color_code",
                       "size_code", "requirement", "unit_cost", "total_cost", "ship_date"], rows)


@router.get("/cost-vs-price", auth=AuthBearer())
@require_permission("mms.report.view")
def cost_vs_price_report(request):
    rows = []
    for c in Costing.objects.filter(status="approved").order_by("-approved_at"):
        row = {
            "style_no": c.style_no,
            "order_no": c.order_no or "",
            "version_no": c.version_no,
            "currency_code": c.currency_code,
            "cost_per_piece": str(c.cost_per_piece),
            "fob_price": str(c.fob_price),
            "buyer_price": str(c.buyer_price) if c.buyer_price is not None else "",
        }
        if c.buyer_price is not None and c.buyer_price:
            row["margin_vs_buyer_pct"] = f"{(((c.buyer_price - c.cost_per_piece) / c.buyer_price) * 100):.2f}"
        else:
            row["margin_vs_buyer_pct"] = ""
        rows.append(row)
    return _maybe_csv(request, "cost-vs-price",
                      ["style_no", "order_no", "version_no", "currency_code", "cost_per_piece",
                       "fob_price", "buyer_price", "margin_vs_buyer_pct"], rows)


@router.get("/samples", auth=AuthBearer())
@require_permission("mms.report.view")
def samples_report(request):
    rows = []
    for s in SampleRequest.objects.all().order_by("due_date"):
        rows.append({
            "sample_no": s.sample_no,
            "style_no": s.style_no,
            "sample_type": s.sample_type,
            "quantity": s.quantity,
            "due_date": s.due_date.isoformat() if s.due_date else "",
            "sent_date": s.sent_date.isoformat() if s.sent_date else "",
            "status": s.status,
            "overdue": "yes" if s.is_overdue else "no",
        })
    return _maybe_csv(request, "samples",
                      ["sample_no", "style_no", "sample_type", "quantity", "due_date",
                       "sent_date", "status", "overdue"], rows)


@router.get("/shipments", auth=AuthBearer())
@require_permission("mms.report.view")
def shipments_report(request, from_date: Optional[date] = None, to_date: Optional[date] = None):
    today = date.today()
    rows = []
    qs = Order.objects.exclude(ship_date__isnull=True).order_by("ship_date")
    if from_date:
        qs = qs.filter(ship_date__gte=from_date)
    if to_date:
        qs = qs.filter(ship_date__lte=to_date)
    for o in qs:
        days_to = (o.ship_date - today).days if o.ship_date else None
        rows.append({
            "order_no": o.order_no,
            "buyer_name": o.buyer_name,
            "ship_date": o.ship_date.isoformat(),
            "status": o.status,
            "days_to_ship": days_to if days_to is not None else "",
            "total_qty": str(o.total_qty),
            "total_value": str(o.total_value),
        })
    return _maybe_csv(request, "shipments",
                      ["order_no", "buyer_name", "ship_date", "status", "days_to_ship",
                       "total_qty", "total_value"], rows)


@router.get("/dashboard", auth=AuthBearer())
@require_permission("mms.dashboard.view")
def dashboard(request):
    order_by_status = dict(Order.objects.values_list("status").annotate(n=Count("id")))
    style_by_status = dict(Style.objects.values_list("status").annotate(n=Count("id")))
    sample_by_status = dict(SampleRequest.objects.values_list("status").annotate(n=Count("id")))

    open_value = Order.objects.filter(status__in=("draft", "confirmed", "in_production")) \
        .aggregate(v=Sum("total_value"))["v"] or Decimal("0")
    total_qty = Order.objects.aggregate(q=Sum("total_qty"))["q"] or Decimal("0")

    overdue_samples = SampleRequest.objects.filter(
        status__in=SampleRequest.OPEN_STATUSES, due_date__lt=date.today()
    ).count()

    top_styles = list(
        Order.objects.filter(lines__isnull=False)
        .values("lines__style_no")
        .annotate(qty=Sum("lines__quantity"), value=Sum("lines__total_value"))
        .order_by("-qty")[:5]
    )
    top_styles = [{"style_no": t["lines__style_no"], "qty": str(t["qty"]), "value": str(t["value"])} for t in top_styles]

    recent_orders = [
        {
            "order_no": o.order_no,
            "buyer_name": o.buyer_name,
            "status": o.status,
            "total_value": str(o.total_value),
            "order_date": o.order_date.isoformat(),
        }
        for o in Order.objects.order_by("-created_at")[:8]
    ]

    bom_by_status = dict(Bom.objects.values_list("status").annotate(n=Count("id")))
    costing_by_status = dict(Costing.objects.values_list("status").annotate(n=Count("id")))

    return {
        "counts": {
            "styles": Style.objects.count(),
            "orders": Order.objects.count(),
            "open_orders": sum(order_by_status.get(s, 0) for s in ("draft", "confirmed", "in_production")),
            "samples": SampleRequest.objects.count(),
            "overdue_samples": overdue_samples,
            "boms": Bom.objects.count(),
            "costings": Costing.objects.count(),
            "open_order_value": str(open_value),
            "total_order_qty": str(total_qty),
        },
        "orders_by_status": [{"label": k, "value": v} for k, v in order_by_status.items()],
        "styles_by_status": [{"label": k, "value": v} for k, v in style_by_status.items()],
        "samples_by_status": [{"label": k, "value": v} for k, v in sample_by_status.items()],
        "bom_by_status": [{"label": k, "value": v} for k, v in bom_by_status.items()],
        "costing_by_status": [{"label": k, "value": v} for k, v in costing_by_status.items()],
        "top_styles": top_styles,
        "recent_orders": recent_orders,
    }