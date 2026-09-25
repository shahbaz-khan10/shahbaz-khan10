"""Material requirement calculation.

For an order, every line is broken into its size quantities. Each approved BOM
item of that line's style applies when it covers the line's color/size (a blank
color/size on the BOM item means "all"). Requirement for each application is:

    consumption × (1 + wastage_pct / 100) × line quantity

and is aggregated per (item, color, size).
"""

from typing import Optional

from .models import Bom


class BomNotFoundError(Exception):
    def __init__(self, style_no: str):
        super().__init__(f"No approved BOM for style {style_no}.")
        self.style_no = style_no


def material_requirement(order) -> dict:
    """Returns the material requirement summary for one order."""
    style_boms: dict[int, Optional[Bom]] = {}
    aggregates: dict[tuple, dict] = {}

    for line in order.lines.prefetch_related("sizes").all():
        bom = style_boms.get(line.style_id)
        if line.style_id not in style_boms:
            bom = (
                Bom.objects
                .filter(style_id=line.style_id, status="approved")
                .order_by("-version_no")
                .first()
            )
            style_boms[line.style_id] = bom
        if bom is None:
            continue
        for size in line.sizes.all():
            for item in bom.items.all():
                if item.color_id and item.color_id != line.color_id:
                    continue
                if item.size_id and item.size_id != size.size_id:
                    continue
                qty = (item.consumption or 0) * (1 + (item.wastage_pct or 0) / 100) * (size.quantity or 0)
                key = (
                    line.style_id, line.style_no, item.item_id, item.item_code, item.item_name,
                    item.uom_code or item.item_unit_code, item.color_id, item.color_code, item.color_name,
                    item.size_id, item.size_code, item.size_name, item.unit_cost,
                )
                agg = aggregates.setdefault(key, {"requirement": 0})
                agg["requirement"] += qty

    rows = []
    total_value = 0
    for key, agg in aggregates.items():
        (
            style_id, style_no, item_id, item_code, item_name, uom_code,
            color_id, color_code, color_name, size_id, size_code, size_name, unit_cost,
        ) = key
        value = agg["requirement"] * (unit_cost or 0)
        total_value += value
        rows.append({
            "style_id": style_id,
            "style_no": style_no,
            "item_id": item_id,
            "item_code": item_code,
            "item_name": item_name,
            "uom_code": uom_code,
            "color_id": color_id,
            "color_code": color_code,
            "color_name": color_name,
            "size_id": size_id,
            "size_code": size_code,
            "size_name": size_name,
            "requirement": agg["requirement"],
            "unit_cost": unit_cost,
            "total_cost": value,
        })

    return {
        "order_id": order.id,
        "order_no": order.order_no,
        "total_items": len(rows),
        "total_cost": total_value,
        "items": rows,
    }