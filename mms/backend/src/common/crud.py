"""Factory for consistent CRUD routers for MMS entities.

Mirrors AMS `common.crud` but gates on `mms.<entity>.<action>` permissions and
records soft-deletes & deletes into the central AMS audit log.
"""

from ninja import Router
from ninja.errors import HttpError

from .audit import record
from .auth import actor, actor_values, request_token


def _bearer():
    from .auth import AuthBearer

    return AuthBearer()


def make_crud_router(
    *,
    entity: str,
    model,
    serializer,
    permission: str,
    tags=None,
    search_fields=("name", "code"),
    fk_assignable=(),
    order_by=("id",),
    create_schema=None,
    update_schema=None,
    uppercase_fields=(),
):
    router = Router(tags=tags or [permission])

    def _require(action):
        from .auth import require_permission

        return require_permission(f"mms.{permission}.{action}")

    def _row(pk):
        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise HttpError(404, f"{entity} not found.")

    @router.get("", auth=_bearer())
    @_require("view")
    def list_items(request, search: str = "", page: int = 1, page_size: int = 20):
        from django.db.models import Q

        qs = model.objects.all().order_by(*order_by)
        search = search.strip()
        if search:
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search})
            qs = qs.filter(q)

        filters = {}
        for key, value in request.GET.items():
            if key in ("search", "page", "page_size"):
                continue
            try:
                field = model._meta.get_field(key)
            except Exception:
                continue
            if field.get_internal_type() == "BooleanField":
                filters[key] = value.lower() in ("1", "true", "yes")
            elif hasattr(field, "remote_field") and field.remote_field:
                filters[f"{key}_id"] = value
            else:
                filters[key] = value
        if filters:
            qs = qs.filter(**filters)

        total = qs.count()
        page_size = max(1, min(page_size, 200))
        page = max(1, page)
        items = [serializer(o) for o in qs[(page - 1) * page_size : page * page_size]]
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size if total else 0,
            },
        }

    @router.get("/{pk}", auth=_bearer())
    @_require("view")
    def get_item(request, pk: int):
        return serializer(_row(pk))

    @router.post("", auth=_bearer())
    @_require("create")
    def create_item(request, payload: create_schema):
        data = payload.model_dump(exclude_unset=True, exclude={"id"})
        data.update(actor_values(request))
        data = _prepare_fks(data, fk_assignable)
        _normalize(data, uppercase_fields)
        try:
            obj = model.objects.create(**data)
        except Exception as exc:
            raise HttpError(400, _sqlexc_message(exc))
        record("create", model._meta.label_lower, obj.pk, str(obj), token=request_token(request))
        return serializer(obj)

    @router.patch("/{pk}", auth=_bearer())
    @_require("edit")
    def update_item(request, pk: int, payload: update_schema):
        obj = _row(pk)
        data = payload.model_dump(exclude_unset=True, exclude={"id"})
        data = _prepare_fks(data, fk_assignable)
        _normalize(data, uppercase_fields)
        for key, value in data.items():
            setattr(obj, key, value)
        try:
            obj.save()
        except Exception as exc:
            raise HttpError(400, _sqlexc_message(exc))
        record("update", model._meta.label_lower, obj.pk, str(obj), token=request_token(request))
        return serializer(obj)

    @router.delete("/{pk}", auth=_bearer())
    @_require("delete")
    def delete_item(request, pk: int):
        obj = _row(pk)
        obj.soft_delete(user=actor(request))
        record("delete", model._meta.label_lower, obj.pk, str(obj), token=request_token(request))
        return {"detail": "Deleted."}

    return router


def _prepare_fks(data: dict, fk_assignable) -> dict:
    clean = {}
    for key, value in data.items():
        if key in fk_assignable and value is not None:
            clean[f"{key}_id"] = value
        else:
            clean[key] = value
    return clean


def _normalize(data: dict, uppercase_fields):
    for field in uppercase_fields:
        if data.get(field) is not None:
            data[field] = str(data[field]).strip().upper()


def _sqlexc_message(exc) -> str:
    msg = str(exc)
    if isinstance(exc, Exception):
        first = msg.split("\n")[0]
        if "UNIQUE" in msg.upper():
            return "A record with that code/name already exists."
        return first[:300]
    return str(exc)[:300]