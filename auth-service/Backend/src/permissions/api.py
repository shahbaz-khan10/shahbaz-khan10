from typing import Optional

from django.db.models import Q
from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel

from audit.middleware import get_client_ip, get_current_user
from audit.models import record
from authentication.api import AuthBearer
from . import rbac
from .models import EmployeeRole, Permission, Role, Service

router = Router(tags=["users & roles"])


class RoleIdsIn(BaseModel):
    role_ids: list[int] = []


def rbac_gate(entity, action):
    from permissions.decorators import require_permission

    return require_permission(f"ams.{entity}.{action}")


# ---------------------------------------------------------------- services
@router.get("/services", auth=AuthBearer())
@rbac_gate("dashboard", "view")
def list_services(request):
    return [{"code": s.code, "name": s.name, "is_active": s.is_active} for s in Service.objects.filter(is_active=True).order_by("code")]


# ---------------------------------------------------------------- permissions
@router.get("/permissions", auth=AuthBearer())
@rbac_gate("role", "manage")
def list_permissions(request, module: str = ""):
    qs = Permission.objects.select_related("module").all()
    if module:
        qs = qs.filter(module__code=module)
    return [
        {
            "id": p.id,
            "module": p.module.code,
            "entity": p.entity,
            "action": p.action,
            "codename": p.codename,
            "name": p.name,
        }
        for p in qs.order_by("module__code", "entity", "action")
    ]


# ---------------------------------------------------------------- users
class UserCreateIn(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    employee_id: int
    role_ids: list[int] = []
    is_active: bool = True
    is_super_admin: bool = False


class UserUpdateIn(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    employee_id: Optional[int] = None
    role_ids: Optional[list[int]] = None
    is_active: Optional[bool] = None
    is_super_admin: Optional[bool] = None


def user_dict(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "employee_id": user.employee_id,
        "employee_code": user.employee.employee_code if user.employee_id else None,
        "department_id": user.employee.department_id if user.employee_id else None,
        "department_name": user.employee.department.name if user.employee_id and user.employee.department_id else None,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active,
        "roles": list(user.assigned_roles.values_list("role_id", flat=True)),
        "role_names": list(user.assigned_roles.values_list("role__name", flat=True)),
        "perms": rbac.effective_permissions(user),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def _req(key):
    from permissions.decorators import require_permission

    return require_permission(key)


@router.get("/users", auth=AuthBearer())
@_req("ams.user.view")
def list_users(request, search: str = "", role_id: Optional[int] = None, page: int = 1, page_size: int = 20):
    qs = (
        UserModel()
        .objects.select_related("employee__department", "employee__designation")
        .prefetch_related("assigned_roles__role")
        .all()
    )
    if search:
        qs = qs.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(employee__full_name__icontains=search)
            | Q(employee__employee_code__icontains=search)
        )
    if role_id:
        qs = qs.filter(assigned_roles__role_id=role_id)
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [user_dict(u) for u in qs.order_by("username")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.get("/users/{pk}", auth=AuthBearer())
@_req("ams.user.view")
def get_user(request, pk: int):
    user = UserModel().objects.select_related("employee").prefetch_related("assigned_roles__role").filter(pk=pk).first()
    if user is None:
        raise HttpError(404, "User not found.")
    return user_dict(user)


@router.post("/users", auth=AuthBearer())
@_req("ams.user.create")
def create_user(request, payload: UserCreateIn):
    from authentication.models import User

    username = payload.username.strip()
    if User.objects.filter(username__iexact=username).exists():
        raise HttpError(400, "Username already exists.")
    if payload.email and User.objects.filter(email__iexact=payload.email.strip()).exists():
        raise HttpError(400, "Email already exists.")

    is_super_admin = False
    if payload.is_super_admin:
        if not request.auth.is_super_admin:
            raise HttpError(403, "Only the platform Super Admin can grant super admin rights.")
        is_super_admin = True

    user = User(username=username, email=payload.email.strip() if payload.email else None, is_active=payload.is_active, is_super_admin=is_super_admin)
    user.set_password(payload.password)
    user.employee_id = payload.employee_id
    user.created_by = request.auth
    user.save()
    _set_roles(request, user, payload.role_ids or [])
    record("create", "authentication.user", user.id, username, actor=request.auth, ip=get_client_ip())
    return user_dict(user)


@router.patch("/users/{pk}", auth=AuthBearer())
@_req("ams.user.edit")
def update_user(request, pk: int, payload: UserUpdateIn):
    from authentication.models import User

    user = User.objects.select_related("employee").filter(pk=pk).first()
    if user is None:
        raise HttpError(404, "User not found.")
    data = payload.model_dump(exclude_unset=True)

    if "username" in data:
        username = data["username"].strip()
        if User.objects.filter(username__iexact=username).exclude(pk=pk).exists():
            raise HttpError(400, "Username already exists.")
        user.username = username
    if "email" in data:
        email = (data["email"] or "").strip() or None
        if email and User.objects.filter(email__iexact=email).exclude(pk=pk).exists():
            raise HttpError(400, "Email already exists.")
        user.email = email
    if data.get("password"):
        user.set_password(data["password"])
    if "employee_id" in data:
        user.employee_id = data["employee_id"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    if "is_super_admin" in data:
        if not request.auth.is_super_admin:
            raise HttpError(403, "Only the platform Super Admin can grant super admin rights.")
        user.is_super_admin = data["is_super_admin"]
    user.save()
    if "role_ids" in data:
        _set_roles(request, user, data["role_ids"] or [])
    record("update", "authentication.user", user.id, user.username, actor=request.auth, ip=get_client_ip())
    return user_dict(user)


@router.delete("/users/{pk}", auth=AuthBearer())
@_req("ams.user.delete")
def delete_user(request, pk: int):
    from authentication.models import RefreshToken, User

    user = User.objects.filter(pk=pk).first()
    if user is None:
        raise HttpError(404, "User not found.")
    if user.is_super_admin:
        raise HttpError(400, "The platform Super Admin cannot be deleted.")
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    RefreshToken.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=now())
    record("delete", "authentication.user", user.id, user.username, actor=request.auth, ip=get_client_ip())
    return {"detail": "User deactivated and sessions revoked."}


@router.post("/users/{pk}/roles", auth=AuthBearer())
@_req("ams.user.edit")
def set_user_roles(request, pk: int, body: RoleIdsIn):
    from authentication.models import User

    user = User.objects.filter(pk=pk).first()
    if user is None:
        raise HttpError(404, "User not found.")
    _set_roles(request, user, body.role_ids or [])
    return user_dict(user)


@router.get("/users/{pk}/permissions", auth=AuthBearer())
@_req("ams.role.view")
def user_permissions(request, pk: int):
    from authentication.models import User

    user = User.objects.filter(pk=pk).first()
    if user is None:
        raise HttpError(404, "User not found.")
    return {"roles": rbac.roles_for_user(user), "perms": rbac.effective_permissions(user)}


def _set_roles(request, user, role_ids: list[int]):
    from django.utils import timezone

    valid = set(Role.objects.filter(is_active=True).values_list("id", flat=True))
    for rid in role_ids:
        if rid not in valid:
            raise HttpError(400, f"Role id {rid} does not exist or is inactive.")
    EmployeeRole.objects.filter(user=user).delete()
    for rid in role_ids:
        EmployeeRole.objects.create(user=user, role_id=rid, granted_by=request.auth, granted_at=timezone.now())


def now():
    from django.utils import timezone

    return timezone.now()


def UserModel():
    from django.apps import apps

    return apps.get_model("authentication", "User")


# ---------------------------------------------------------------- roles
class RoleIn(BaseModel):
    name: str
    description: str = ""
    is_active: bool = True


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RolePermsIn(BaseModel):
    permission_ids: list[int] = []


def role_dict(o: Role) -> dict:
    return {
        "id": o.id,
        "name": o.name,
        "description": o.description,
        "is_active": o.is_active,
        "is_system": o.is_system,
        "permission_count": o.role_permissions.count(),
        "user_count": o.user_roles.count(),
    }


@router.get("/roles", auth=AuthBearer())
@_req("ams.role.view")
def list_roles(request, search: str = "", page: int = 1, page_size: int = 50):
    qs = Role.objects.all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [role_dict(o) for o in qs.order_by("name")[(page - 1) * page_size : page * page_size]]
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0}}


@router.post("/roles", auth=AuthBearer())
@_req("ams.role.create")
def create_role(request, payload: RoleIn):
    name = payload.name.strip()
    if Role.objects.filter(name__iexact=name).exists():
        raise HttpError(400, "A role with this name already exists.")
    role = Role.objects.create(name=name, description=payload.description, is_active=payload.is_active, created_by=request.auth)
    return role_dict(role)


@router.get("/roles/{pk}", auth=AuthBearer())
@_req("ams.role.view")
def get_role(request, pk: int):
    role = Role.objects.filter(pk=pk).first()
    if role is None:
        raise HttpError(404, "Role not found.")
    return {**role_dict(role), "permissions": list(role.role_permissions.values_list("permission_id", flat=True))}


@router.patch("/roles/{pk}", auth=AuthBearer())
@_req("ams.role.edit")
def update_role(request, pk: int, payload: RoleUpdate):
    role = Role.objects.filter(pk=pk).first()
    if role is None:
        raise HttpError(404, "Role not found.")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        name = data["name"].strip()
        if Role.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            raise HttpError(400, "A role with this name already exists.")
        role.name = name
    if "description" in data:
        role.description = data["description"]
    if "is_active" in data:
        role.is_active = data["is_active"]
    role.save()
    return role_dict(role)


@router.delete("/roles/{pk}", auth=AuthBearer())
@_req("ams.role.delete")
def delete_role(request, pk: int):
    role = Role.objects.filter(pk=pk).first()
    if role is None:
        raise HttpError(404, "Role not found.")
    if role.is_system:
        raise HttpError(400, "System roles cannot be deleted; deactivate them instead.")
    role.soft_delete(user=get_current_user())
    record("delete", "permissions.role", pk, role.name, actor=request.auth, ip=get_client_ip())
    return {"detail": "Role deleted."}


@router.put("/roles/{pk}/permissions", auth=AuthBearer())
@_req("ams.role.manage")
def set_role_permissions(request, pk: int, body: RolePermsIn):
    role = Role.objects.filter(pk=pk).first()
    if role is None:
        raise HttpError(404, "Role not found.")
    valid = set(Permission.objects.values_list("id", flat=True))
    for pid in body.permission_ids:
        if pid not in valid:
            raise HttpError(400, f"Permission id {pid} does not exist.")
    from .models import RolePermission

    RolePermission.objects.filter(role=role).delete()
    for pid in body.permission_ids:
        RolePermission.objects.create(role=role, permission_id=pid)
    record("update", "permissions.role", role.id, role.name, actor=request.auth, ip=get_client_ip(), notes="permissions updated")
    return role_dict(role)