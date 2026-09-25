"""Seed demo merchandising data (dev only). Idempotent.

Prepares the minimum AMS masters it needs (buyer, item category, a few items)
through the AMS API using the demo seed account, then creates MMS domain
records directly in the MMS database. AMS must be reachable.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from bom.models import Bom, BomItem
from common.ams_client import ams
from common.audit import record
from costing.models import Costing, CostingLine
from orders.models import Order, OrderLine, OrderLineSize, recalc_line, recalc_order
from samples.models import SampleRequest
from styles.models import Style, StyleVersion

logger = logging.getLogger("seeds")

D = Decimal


def _find(data, **kw):
    if not data:
        return None
    for item in data.get("items", []):
        if all(item.get(k) == v for k, v in kw.items()):
            return item
    return None


def _ensure_buyer(request_, token):
    existing = _find(ams.list_buyers(token), code="DEMO-BUY")
    if existing:
        return existing
    usd = _find(ams.list_currencies(token), code="USD")
    data = {
        "code": "DEMO-BUY",
        "name": "Demo Apparel Ltd",
        "country": "United States",
        "currency_id": usd["id"] if usd else None,
        "payment_terms": "30% advance, balance against documents",
    }
    created = ams.request("POST", "/buyers", token=token, json=data)
    logger.info("Created AMS buyer DEMO-BUY: %s", created)
    return created


def _ensure_category(token):
    existing = _find(ams.request("GET", "/item-categories", token=token), code="RAW-MAT")
    if existing:
        return existing
    data = {"code": "RAW-MAT", "name": "Raw Material"}
    created = ams.request("POST", "/item-categories", token=token, json=data)
    logger.info("Created AMS item category RAW-MAT: %s", created)
    return created


def _ensure_items(token, category_id):
    units = ams.request("GET", "/units-of-measure", token=token)
    meter = _find(units, code="MTR") or _find(units, code="YDS")
    pc = _find(units, code="PCS")
    if not meter or not pc:
        logger.warning("Skipping item seeding: MTR/PCS units missing in AMS.")
        return {}

    specs = [
        ("FAB-COTTON-140", "Cotton Fabric 140 GSM", meter["id"], D("3.20"), D("4.00")),
        ("TRIM-03BUTTON", "General 2Hole Button", pc["id"], D("0.02"), D("0.05")),
        ("TRIM-POLYBAG", "Poly Bag 18x24", pc["id"], D("0.05"), D("0.08")),
        ("THREAD-40", "Sewing Thread NE 40/2", pc["id"], D("0.40"), D("0.60")),
    ]
    created = {}
    for code, name, unit_id, purchase, sale in specs:
        found = _find(ams.list_items(token, search=code), code=code)
        if found:
            created[code] = found
            continue
        data = {
            "code": code, "name": name, "category_id": category_id, "unit_id": unit_id,
            "purchase_price": str(purchase), "sale_price": str(sale), "is_active": True,
        }
        item = ams.request("POST", "/items", token=token, json=data)
        logger.info("Created AMS item %s: %s", code, item)
        created[code] = item
    return created


class Command(BaseCommand):
    help = "Seed demo MMS data (styles, orders, BOM, costing, samples) idempotently."

    def handle(self, *args, **options):
        login = ams.login(settings.AMS_SEED_USERNAME, settings.AMS_SEED_PASSWORD)
        if not login or not login.get("token"):
            self.stderr.write(self.style.ERROR(
                "Could not log into AMS as %s. Is AMS running at %s?"
                % (settings.AMS_SEED_USERNAME, settings.AMS_API_URL)
            ))
            return
        token = login["token"]
        user = ams.whoami(token) or {}
        actor = {"id": user.get("id"), "full_name": user.get("full_name") or user.get("username", "")}

        # --- AMS masters (create-if-missing through AMS) --------------------
        buyer = _ensure_buyer(ams, token)
        category = _ensure_category(token)
        items = _ensure_items(token, category["id"])
        fabric = items.get("FAB-COTTON-140")
        buttons = items.get("TRIM-03BUTTON")
        polybag = items.get("TRIM-POLYBAG")
        thread = items.get("THREAD-40")

        colors = ams.list_colors(token).get("items", [])[:2]
        sizes = ams.list_sizes(token).get("items", [])[:4]
        currency = _find(ams.list_currencies(token), code="USD") or ams.list_currencies(token)["items"][0]
        navy, white = colors[0], colors[1] if len(colors) > 1 else colors[0]
        if len(sizes) < 4 or not colors or not buyer or not fabric:
            self.stderr.write(self.style.ERROR("Required AMS masters missing; seed aborted."))
            return
        s_sz, m_sz, l_sz, xl_sz = sizes[0], sizes[1], sizes[2], sizes[3]

        today = timezone.localdate()
        kwargs = {"created_by": actor["id"], "created_by_name": actor["full_name"]}

        # --- Styles ----------------------------------------------------------
        if not Style.objects.filter(style_no="STY-0001").exists():
            Style.objects.create(
                style_no="STY-0001", buyer_id=buyer["id"], buyer_code=buyer.get("code", ""),
                buyer_name=buyer.get("name", ""), description="Men's Cotton Oxford Shirt",
                category="shirt", season="SS-2026", fabric_type="Cotton 140 GSM",
                status="sample_approved", version_no=1, **kwargs,
            )
            StyleVersion.objects.create(style_id=Style.objects.get(style_no="STY-0001").id,
                                        version_no=1, notes="Initial style",
                                        changed_by=actor["id"], changed_by_name=actor["full_name"])
            record("create", "styles.style", "STY-0001", "Men's Cotton Oxford Shirt", token=token)
        if not Style.objects.filter(style_no="STY-0002").exists():
            Style.objects.create(
                style_no="STY-0002", buyer_id=buyer["id"], buyer_code=buyer.get("code", ""),
                buyer_name=buyer.get("name", ""), description="Women's Woven Trousers",
                category="trouser", season="AW-2026", fabric_type="Gabardine",
                status="active", version_no=1, **kwargs,
            )
            record("create", "styles.style", "STY-0002", "Women's Woven Trousers", token=token)

        style1 = Style.objects.get(style_no="STY-0001")
        style2 = Style.objects.get(style_no="STY-0002")

        # --- Buyer orders (size-color matrix) --------------------------------
        def _make_order(order_no, style, qi, color, price, sizes_qty, po_no, status):
            if Order.objects.filter(order_no=order_no).exists():
                return Order.objects.get(order_no=order_no)
            order = Order.objects.create(
                order_no=order_no, buyer_po_no=po_no, buyer_id=buyer["id"],
                buyer_code=buyer.get("code", ""), buyer_name=buyer.get("name", ""),
                order_date=today, ship_date=today + timedelta(days=45),
                currency_id=currency["id"], currency_code=currency.get("code", ""),
                payment_terms="30% advance", status=status, **kwargs,
            )
            line = OrderLine.objects.create(
                order=order, style_id=style.id, style_no=style.style_no,
                style_name=style.description, color_id=color["id"], color_code=color.get("code", ""),
                color_name=color.get("name", ""), unit_price=price,
            )
            for size, qty in sizes_qty:
                OrderLineSize.objects.create(
                    line=line, size_id=size["id"], size_code=size.get("code", ""),
                    size_name=size.get("name", ""), quantity=D(str(qty)),
                )
            recalc_order(order)
            record("create", "orders.order", order.pk, order_no, token=token)
            return order

        order1 = _make_order("ORD-2026-0001", style1, today, navy, D("12.50"),
                             [(s_sz, 300), (m_sz, 400), (l_sz, 200), (xl_sz, 100)], "PO-1001", "confirmed")
        order2 = _make_order("ORD-2026-0002", style2, today, white, D("18.00"),
                             [(s_sz, 150), (m_sz, 200), (l_sz, 150)], "PO-1002", "draft")

        # --- BOM (approved, locked) -----------------------------------------
        if not Bom.objects.filter(style_id=style1.id).exists() and fabric and buttons:
            bom = Bom.objects.create(
                style_id=style1.id, style_no=style1.style_no, style_name=style1.description,
                version_no=1, status="approved", notes="Demo approved BOM",
                approved_by=actor["id"], approved_by_name=actor["full_name"], approved_at=timezone.now(),
                **kwargs,
            )
            specs = [
                (fabric, None, None, D("1.60"), D("5"), D("3.20")),
                (buttons, None, None, D("8.00"), D("2"), D("0.02")),
                (polybag, None, None, D("1.00"), D("1"), D("0.05")),
                (thread, None, None, D("0.80"), D("3"), D("0.40")),
            ]
            for item, color_id, size_id, consumption, waste, cost in specs:
                BomItem.objects.create(
                    bom=bom, item_id=item["id"], item_code=item.get("code", ""),
                    item_name=item.get("name", ""),
                    item_unit_code=(item.get("unit_code") or ""), uom_code=(item.get("unit_code") or ""),
                    color_id=color_id, size_id=size_id, consumption=consumption,
                    wastage_pct=D(waste), unit_cost=cost,
                )
            record("create", "bom.bom", bom.pk, str(bom), token=token)

        # --- Costing (approved) ---------------------------------------------
        if not Costing.objects.filter(style_id=style1.id).exists():
            costing = Costing.objects.create(
                style_id=style1.id, style_no=style1.style_no, style_name=style1.description,
                order_id=order1.id, order_no=order1.order_no, version_no=1,
                currency_id=currency["id"], currency_code=currency.get("code", ""),
                exchange_rate=D("1.00"), margin_pct=D("20"), buyer_price=D("12.50"),
                status="approved", notes="Demo costing", approved_by=actor["id"],
                approved_by_name=actor["full_name"], approved_at=timezone.now(), **kwargs,
            )
            lines = [
                (fabric, "fabric", "Fabric consumption", D("1.60"), D("3.20")),
                (buttons, "trims", "Buttons", D("8.00"), D("0.02")),
                (polybag, "trims", "Poly bag", D("1.00"), D("0.05")),
                (thread, "trims", "Sewing thread", D("0.80"), D("0.40")),
                (None, "cm", "Cut & make", D("1"), D("2.00")),
                (None, "overhead", "Factory overhead", D("1"), D("0.50")),
                (None, "freight", "Air freight", D("1"), D("0.30")),
            ]
            for item, component, desc, consumption, unit_cost in lines:
                CostingLine.objects.create(
                    costing=costing, component=component, description=desc,
                    item_id=item["id"] if item else None,
                    item_code=item.get("code", "") if item else "",
                    item_name=item.get("name", "") if item else "",
                    uom_code=item.get("unit_code", "") if item else "",
                    consumption=consumption, unit_cost=unit_cost,
                    amount=consumption * unit_cost,
                )
            costing.recalc()
            record("create", "costing.costing", costing.pk, str(costing), token=token)

        # --- Samples ---------------------------------------------------------
        if not SampleRequest.objects.filter(sample_no="SPL-2026-0001").exists():
            SampleRequest.objects.create(
                sample_no="SPL-2026-0001", style_id=style1.id, style_no=style1.style_no,
                style_name=style1.description, sample_type="proto", quantity=1,
                due_date=today - timedelta(days=2), buyer_comments="Proto for fit review.",
                status="in_progress", **kwargs,
            )
            record("create", "samples.samplerequest", "SPL-2026-0001", "Proto", token=token)
        if not SampleRequest.objects.filter(sample_no="SPL-2026-0002").exists():
            SampleRequest.objects.create(
                sample_no="SPL-2026-0002", style_id=style2.id, style_no=style2.style_no,
                style_name=style2.description, sample_type="fit", quantity=2,
                due_date=today + timedelta(days=10), buyer_comments="Fit sample.",
                status="requested", **kwargs,
            )
            record("create", "samples.samplerequest", "SPL-2026-0002", "Fit sample", token=token)

        # Repair line/order totals (re-seeding is idempotent; earlier runs
        # before recalc_line existed may have left zeros).
        for order in Order.objects.all():
            for line in order.lines.all():
                recalc_line(line)
            recalc_order(order)
        for costing in Costing.objects.filter(order_id__isnull=False):
            costing.recalc()

        self.stdout.write(self.style.SUCCESS(
            "Demo data ready: 2 styles, 2 orders, 1 approved BOM, 1 approved "
            "costing, 2 samples. AMS masters ensured (buyer DEMO-BUY, 4 items)."
        ))