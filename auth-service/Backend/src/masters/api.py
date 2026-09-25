from datetime import date
from decimal import Decimal
from typing import Optional

from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel, Field

from authentication.api import AuthBearer
from common.crud import make_crud_router
from permissions.decorators import require_permission

from .models import (
    Buyer,
    Color,
    Currency,
    ExchangeRate,
    Item,
    ItemCategory,
    Size,
    SizeGroup,
    SizeGroupSize,
    Supplier,
    UnitOfMeasure,
    UomConversion,
    Warehouse,
)

router = Router(tags=["masters"])


# ---------------------------------------------------------------- currencies
class CurrencyIn(BaseModel):
    code: str
    name: str
    symbol: str = ""
    is_base: bool = False
    is_active: bool = True


class CurrencyUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    is_base: Optional[bool] = None
    is_active: Optional[bool] = None


def currency_dict(o: Currency) -> dict:
    return {"id": o.id, "code": o.code, "name": o.name, "symbol": o.symbol, "is_base": o.is_base, "is_active": o.is_active}


currency_router = make_crud_router(
    entity="currency",
    model=Currency,
    serializer=currency_dict,
    permission="currency",
    create_schema=CurrencyIn,
    update_schema=CurrencyUpdate,
    search_fields=("code", "name"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- exchange rates
class ExchangeRateIn(BaseModel):
    from_currency_id: int
    to_currency_id: int
    rate: Decimal = Field(gt=0)
    effective_date: date
    notes: str = ""


class ExchangeRateUpdate(BaseModel):
    from_currency_id: Optional[int] = None
    to_currency_id: Optional[int] = None
    rate: Optional[Decimal] = Field(default=None, gt=0)
    effective_date: Optional[date] = None
    notes: Optional[str] = None


def exchange_rate_dict(o: ExchangeRate) -> dict:
    return {
        "id": o.id,
        "from_currency_id": o.from_currency_id,
        "from_currency_code": o.from_currency.code if o.from_currency_id else None,
        "to_currency_id": o.to_currency_id,
        "to_currency_code": o.to_currency.code if o.to_currency_id else None,
        "rate": str(o.rate),
        "effective_date": o.effective_date.isoformat(),
        "notes": o.notes,
    }


def _validate_rate(data: dict):
    if data.get("from_currency_id") is not None and data["from_currency_id"] == data.get("to_currency_id"):
        raise HttpError(400, "From and to currency must be different.")


@router.get("/exchange-rates", auth=AuthBearer())
@require_permission("ams.exchange_rate.view")
def list_exchange_rates(request, from_currency_id: Optional[int] = None, to_currency_id: Optional[int] = None, page: int = 1, page_size: int = 20):
    qs = ExchangeRate.objects.select_related("from_currency", "to_currency").all()
    if from_currency_id:
        qs = qs.filter(from_currency_id=from_currency_id)
    if to_currency_id:
        qs = qs.filter(to_currency_id=to_currency_id)
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [exchange_rate_dict(o) for o in qs.order_by("-effective_date")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.get("/exchange-rates/{pk}", auth=AuthBearer())
@require_permission("ams.exchange_rate.view")
def get_exchange_rate(request, pk: int):
    try:
        return exchange_rate_dict(ExchangeRate.objects.select_related("from_currency", "to_currency").get(pk=pk))
    except ExchangeRate.DoesNotExist:
        raise HttpError(404, "Exchange rate not found.")


@router.post("/exchange-rates", auth=AuthBearer())
@require_permission("ams.exchange_rate.create")
def create_exchange_rate(request, payload: ExchangeRateIn):
    data = payload.model_dump(exclude_unset=True)
    _validate_rate(data)
    data["from_currency"] = Currency.objects.get(pk=data.pop("from_currency_id"))
    data["to_currency"] = Currency.objects.get(pk=data.pop("to_currency_id"))
    try:
        obj = ExchangeRate.objects.create(**data)
    except Exception as exc:
        raise HttpError(400, _rate_error(exc))
    return exchange_rate_dict(obj)


@router.patch("/exchange-rates/{pk}", auth=AuthBearer())
@require_permission("ams.exchange_rate.edit")
def update_exchange_rate(request, pk: int, payload: ExchangeRateUpdate):
    try:
        obj = ExchangeRate.objects.select_related("from_currency", "to_currency").get(pk=pk)
    except ExchangeRate.DoesNotExist:
        raise HttpError(404, "Exchange rate not found.")
    data = payload.model_dump(exclude_unset=True)
    if "from_currency_id" in data:
        data["from_currency"] = Currency.objects.get(pk=data.pop("from_currency_id"))
    if "to_currency_id" in data:
        data["to_currency"] = Currency.objects.get(pk=data.pop("to_currency_id"))
    _validate_rate(data)
    for key, value in data.items():
        setattr(obj, key, value)
    try:
        obj.save()
    except Exception as exc:
        raise HttpError(400, _rate_error(exc))
    return exchange_rate_dict(obj)


@router.delete("/exchange-rates/{pk}", auth=AuthBearer())
@require_permission("ams.exchange_rate.delete")
def delete_exchange_rate(request, pk: int):
    from audit.middleware import get_client_ip, get_current_user
    from audit.models import record

    try:
        obj = ExchangeRate.objects.get(pk=pk)
    except ExchangeRate.DoesNotExist:
        raise HttpError(404, "Exchange rate not found.")
    obj.soft_delete(user=get_current_user())
    record("delete", "masters.exchangerate", pk, str(obj), actor=get_current_user(), ip=get_client_ip())
    return {"detail": "Deleted."}


def _rate_error(exc) -> str:
    return "A rate for this currency pair and date already exists." if "UNIQUE" in str(exc).upper() else str(exc)[:300]


# ---------------------------------------------------------------- buyers
class BuyerIn(BaseModel):
    code: str
    name: str
    contact_person: str = ""
    contact_phone: str = ""
    email: str = ""
    country: str = ""
    city: str = ""
    currency_id: Optional[int] = None
    payment_terms: str = ""
    is_active: bool = True


class BuyerUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    email: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    currency_id: Optional[int] = None
    payment_terms: Optional[str] = None
    is_active: Optional[bool] = None


def buyer_dict(o: Buyer) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "contact_person": o.contact_person,
        "contact_phone": o.contact_phone,
        "email": o.email,
        "country": o.country,
        "city": o.city,
        "currency_id": o.currency_id,
        "currency_code": o.currency.code if o.currency_id else None,
        "payment_terms": o.payment_terms,
        "is_active": o.is_active,
    }


buyer_router = make_crud_router(
    entity="buyer",
    model=Buyer,
    serializer=buyer_dict,
    permission="buyer",
    create_schema=BuyerIn,
    update_schema=BuyerUpdate,
    fk_assignable=("currency",),
    search_fields=("name", "code", "contact_person", "country"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- suppliers
class SupplierIn(BaseModel):
    code: str
    name: str
    type: str = "general"
    contact_person: str = ""
    contact_phone: str = ""
    email: str = ""
    address: str = ""
    country: str = ""
    city: str = ""
    currency_id: Optional[int] = None
    payment_terms: str = ""
    ntn: str = ""
    gst: str = ""
    is_active: bool = True


class SupplierUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    currency_id: Optional[int] = None
    payment_terms: Optional[str] = None
    ntn: Optional[str] = None
    gst: Optional[str] = None
    is_active: Optional[bool] = None


def supplier_dict(o: Supplier) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "type": o.type,
        "contact_person": o.contact_person,
        "contact_phone": o.contact_phone,
        "email": o.email,
        "address": o.address,
        "country": o.country,
        "city": o.city,
        "currency_id": o.currency_id,
        "currency_code": o.currency.code if o.currency_id else None,
        "payment_terms": o.payment_terms,
        "ntn": o.ntn,
        "gst": o.gst,
        "is_active": o.is_active,
    }


supplier_router = make_crud_router(
    entity="supplier",
    model=Supplier,
    serializer=supplier_dict,
    permission="supplier",
    create_schema=SupplierIn,
    update_schema=SupplierUpdate,
    fk_assignable=("currency",),
    search_fields=("name", "code", "contact_person"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- item categories
class ItemCategoryIn(BaseModel):
    code: str
    name: str
    parent_id: Optional[int] = None
    is_active: bool = True


class ItemCategoryUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


def item_category_dict(o: ItemCategory) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "parent_id": o.parent_id,
        "parent_name": o.parent.name if o.parent_id else None,
        "is_active": o.is_active,
    }


item_category_router = make_crud_router(
    entity="item_category",
    model=ItemCategory,
    serializer=item_category_dict,
    permission="item_category",
    create_schema=ItemCategoryIn,
    update_schema=ItemCategoryUpdate,
    fk_assignable=("parent",),
    search_fields=("name", "code"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- units of measure
class UnitIn(BaseModel):
    code: str
    name: str
    dimension: str = "count"
    is_base: bool = False
    is_active: bool = True


class UnitUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    dimension: Optional[str] = None
    is_base: Optional[bool] = None
    is_active: Optional[bool] = None


def unit_dict(o: UnitOfMeasure) -> dict:
    return {"id": o.id, "code": o.code, "name": o.name, "dimension": o.dimension, "is_base": o.is_base, "is_active": o.is_active}


unit_router = make_crud_router(
    entity="unit_of_measure",
    model=UnitOfMeasure,
    serializer=unit_dict,
    permission="unit_of_measure",
    create_schema=UnitIn,
    update_schema=UnitUpdate,
    search_fields=("code", "name"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- uom conversions
class UomConversionIn(BaseModel):
    from_uom_id: int
    to_uom_id: int
    factor: Decimal = Field(gt=0)


class UomConversionUpdate(BaseModel):
    from_uom_id: Optional[int] = None
    to_uom_id: Optional[int] = None
    factor: Optional[Decimal] = Field(default=None, gt=0)


def uom_conversion_dict(o: UomConversion) -> dict:
    return {
        "id": o.id,
        "from_uom_id": o.from_uom_id,
        "from_uom_code": o.from_uom.code if o.from_uom_id else None,
        "to_uom_id": o.to_uom_id,
        "to_uom_code": o.to_uom.code if o.to_uom_id else None,
        "factor": str(o.factor),
    }


uom_conversion_router = make_crud_router(
    entity="uom_conversion",
    model=UomConversion,
    serializer=uom_conversion_dict,
    permission="uom_conversion",
    create_schema=UomConversionIn,
    update_schema=UomConversionUpdate,
    fk_assignable=("from_uom", "to_uom"),
    search_fields=(),
)


# ---------------------------------------------------------------- colors
class ColorIn(BaseModel):
    code: str
    name: str
    hex: str = ""
    is_active: bool = True


class ColorUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    hex: Optional[str] = None
    is_active: Optional[bool] = None


def color_dict(o: Color) -> dict:
    return {"id": o.id, "code": o.code, "name": o.name, "hex": o.hex, "is_active": o.is_active}


color_router = make_crud_router(
    entity="color",
    model=Color,
    serializer=color_dict,
    permission="color",
    create_schema=ColorIn,
    update_schema=ColorUpdate,
    search_fields=("name", "code"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- sizes
class SizeIn(BaseModel):
    code: str
    name: str
    sort_order: int = 0


class SizeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    sort_order: Optional[int] = None


def size_dict(o: Size) -> dict:
    return {"id": o.id, "code": o.code, "name": o.name, "sort_order": o.sort_order}


size_router = make_crud_router(
    entity="size",
    model=Size,
    serializer=size_dict,
    permission="size",
    create_schema=SizeIn,
    update_schema=SizeUpdate,
    search_fields=("code", "name"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- size groups
class SizeGroupIn(BaseModel):
    name: str
    size_ids: list[int] = []


class SizeGroupUpdate(BaseModel):
    name: Optional[str] = None
    size_ids: Optional[list[int]] = None


def size_group_dict(o: SizeGroup) -> dict:
    sizes = list(o.group_sizes.select_related("size").order_by("sort_order"))
    return {
        "id": o.id,
        "name": o.name,
        "sizes": [{"id": s.size.id, "code": s.size.code, "name": s.size.name} for s in sizes],
    }


@router.get("/size-groups", auth=AuthBearer())
@require_permission("ams.size_group.view")
def list_size_groups(request, search: str = "", page: int = 1, page_size: int = 20):
    qs = SizeGroup.objects.all()
    if search:
        qs = qs.filter(name__icontains=search)
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [size_group_dict(o) for o in qs.order_by("name")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.post("/size-groups", auth=AuthBearer())
@require_permission("ams.size_group.create")
def create_size_group(request, payload: SizeGroupIn):
    group = SizeGroup.objects.create(name=payload.name.strip())
    _set_group_sizes(group, payload.size_ids or [])
    return size_group_dict(group)


@router.patch("/size-groups/{pk}", auth=AuthBearer())
@require_permission("ams.size_group.edit")
def update_size_group(request, pk: int, payload: SizeGroupUpdate):
    try:
        group = SizeGroup.objects.get(pk=pk)
    except SizeGroup.DoesNotExist:
        raise HttpError(404, "Size group not found.")
    if payload.name is not None:
        group.name = payload.name.strip()
        group.save()
    if payload.size_ids is not None:
        _set_group_sizes(group, payload.size_ids)
    return size_group_dict(group)


@router.delete("/size-groups/{pk}", auth=AuthBearer())
@require_permission("ams.size_group.delete")
def delete_size_group(request, pk: int):
    try:
        group = SizeGroup.objects.get(pk=pk)
    except SizeGroup.DoesNotExist:
        raise HttpError(404, "Size group not found.")
    group.group_sizes.all().delete()
    group.soft_delete()
    return {"detail": "Deleted."}


def _set_group_sizes(group: SizeGroup, size_ids: list[int]):
    group.group_sizes.all().delete()
    for index, size_id in enumerate(size_ids):
        if not Size.objects.filter(pk=size_id).exists():
            raise HttpError(400, f"Size id {size_id} does not exist.")
        SizeGroupSize.objects.create(size_group=group, size_id=size_id, sort_order=index)


# ---------------------------------------------------------------- warehouses
class WarehouseIn(BaseModel):
    code: str
    name: str
    type: str = "other"
    location: str = ""
    address: str = ""
    manager_id: Optional[int] = None
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


def warehouse_dict(o: Warehouse) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "type": o.type,
        "location": o.location,
        "address": o.address,
        "manager_id": o.manager_id,
        "manager_name": o.manager.full_name if o.manager_id else None,
        "is_active": o.is_active,
    }


warehouse_router = make_crud_router(
    entity="warehouse",
    model=Warehouse,
    serializer=warehouse_dict,
    permission="warehouse",
    create_schema=WarehouseIn,
    update_schema=WarehouseUpdate,
    fk_assignable=("manager",),
    search_fields=("name", "code", "location"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- items
class ItemIn(BaseModel):
    code: str
    name: str
    description: str = ""
    category_id: int
    unit_id: int
    color_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")
    reorder_level: Decimal = Decimal("0")
    is_active: bool = True


class ItemUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    unit_id: Optional[int] = None
    color_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    reorder_level: Optional[Decimal] = None
    is_active: Optional[bool] = None


def item_dict(o: Item) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "description": o.description,
        "category_id": o.category_id,
        "category_name": o.category.name if o.category_id else None,
        "unit_id": o.unit_id,
        "unit_code": o.unit.code if o.unit_id else None,
        "color_id": o.color_id,
        "color_name": o.color.name if o.color_id else None,
        "supplier_id": o.supplier_id,
        "supplier_name": o.supplier.name if o.supplier_id else None,
        "purchase_price": str(o.purchase_price),
        "sale_price": str(o.sale_price),
        "reorder_level": str(o.reorder_level),
        "is_active": o.is_active,
    }


item_router = make_crud_router(
    entity="item",
    model=Item,
    serializer=item_dict,
    permission="item",
    create_schema=ItemIn,
    update_schema=ItemUpdate,
    fk_assignable=("category", "unit", "color", "supplier"),
    search_fields=("code", "name"),
    uppercase_fields=("code",),
)