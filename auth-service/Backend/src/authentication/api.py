from ninja import Router
from ninja.errors import HttpError
from ninja.security import HttpBearer
from pydantic import BaseModel

from audit import models as audit_models
from audit.middleware import set_current_user
from permissions import rbac
from permissions.models import Role

from .jwt_utils import (
    blacklist_access_token,
    mint_access_token,
    mint_refresh_token,
    verify_access_token,
    verify_refresh_token,
)
from .models import User
from .rate_limit import limiter, login_key

router = Router(tags=["auth"])


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        payload = verify_access_token(token)
        if not payload:
            return None
        try:
            user = User.objects.prefetch_related("employee").get(
                id=payload.get("user_id"), is_active=True
            )
        except User.DoesNotExist:
            return None
        set_current_user(user, request)
        return user

    def authenticate_header(self, request):
        return "Bearer"


def _user_payload(user: User) -> dict:
    emp = user.employee
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "employee": (
            {
                "id": emp.id,
                "employee_code": emp.employee_code,
                "department": emp.department.name if emp.department_id else None,
                "department_id": emp.department_id,
                "designation": emp.designation.name if emp.designation_id else None,
                "designation_id": emp.designation_id,
            }
            if emp
            else None
        ),
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active,
        "roles": rbac.roles_for_user(user),
        "perms": rbac.effective_permissions(user),
    }


class LoginIn(BaseModel):
    identifier: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str
    access_token: str = ""


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class ResetPasswordIn(BaseModel):
    user_id: int
    new_password: str


def _client_ip(request):
    return (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP", "")
        or request.META.get("REMOTE_ADDR")
    )


@router.post("/login", auth=None, description="Rate-limited username/email + password login.")
def login(request, payload: LoginIn):
    ip = _client_ip(request)
    allowed, remaining, retry_after = limiter.hit(login_key(ip))
    if not allowed:
        raise HttpError(429, f"Too many login attempts. Try again in {retry_after}s.")

    identifier = payload.identifier.strip()
    user = (
        User.objects.filter(username__iexact=identifier).first()
        or User.objects.filter(email__iexact=identifier).first()
    )
    if user is None or not user.is_active:
        audit_models.record("login", "authentication.user", identifier, actor=None, ip=ip, notes="failed")
        raise HttpError(401, "Invalid credentials.")

    if user.is_locked():
        raise HttpError(423, "Account locked due to repeated failures. Try later or contact an admin.")

    if not user.check_password(payload.password):
        user.record_failed_login()
        audit_models.record("login", "authentication.user", user.id, str(user), actor=None, ip=ip, notes="failed")
        raise HttpError(401, "Invalid credentials.")

    user.record_successful_login()
    access_token = mint_access_token(user)
    refresh_token = mint_refresh_token(user, ip_address=ip, user_agent=request.headers.get("User-Agent", ""))
    audit_models.record("login", "authentication.user", user.id, user.username, actor=user, ip=ip, notes="success")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _user_payload(user),
    }


@router.post("/refresh", auth=None)
def refresh(request, payload: RefreshIn):
    result = verify_refresh_token(payload.refresh_token)
    if result is None:
        raise HttpError(401, "Invalid or expired refresh token.")
    user, row = result
    row.revoke()  # rotate
    access_token = mint_access_token(user)
    refresh_token = mint_refresh_token(user, ip_address=_client_ip(request))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _user_payload(user),
    }


@router.post("/logout", auth=AuthBearer())
def logout(request, payload: LogoutIn):
    user = request.auth
    if payload.access_token:
        blacklist_access_token(payload.access_token)
    if payload.refresh_token:
        result = verify_refresh_token(payload.refresh_token)
        if result:
            _, row = result
            row.revoke()
    audit_models.record("logout", "authentication.user", user.id, user.username, actor=user, ip=_client_ip(request))
    return {"detail": "Logged out."}


@router.get("/me", auth=AuthBearer())
def me(request):
    return _user_payload(request.auth)


@router.post("/change-password", auth=AuthBearer())
def change_password(request, payload: ChangePasswordIn):
    user = request.auth
    if not user.check_password(payload.current_password):
        raise HttpError(400, "Current password is incorrect.")
    _validate_new_password(payload.new_password)
    user.set_password(payload.new_password)
    user.save(update_fields=["password_hash", "updated_at"])
    audit_models.record(
        "password_change", "authentication.user", user.id, user.username, actor=user, ip=_client_ip(request)
    )
    return {"detail": "Password changed."}


@router.post("/reset-password", auth=AuthBearer())
def reset_password(request, payload: ResetPasswordIn):
    actor = request.auth
    if not rbac.user_has_permission(actor, "ams.user.edit"):
        raise HttpError(403, "You need the 'ams.user.edit' permission to reset passwords.")
    user = User.objects.filter(id=payload.user_id).first()
    if user is None:
        raise HttpError(404, "User not found.")
    _validate_new_password(payload.new_password)
    user.set_password(payload.new_password)
    user.locked_until = None
    user.failed_login_attempts = 0
    user.save(update_fields=["password_hash", "locked_until", "failed_login_attempts", "updated_at"])
    audit_models.record(
        "password_reset",
        "authentication.user",
        user.id,
        user.username,
        actor=actor,
        ip=_client_ip(request),
    )
    return {"detail": "Password reset."}


def _validate_new_password(value: str):
    if len(value) < 8:
        raise HttpError(400, "Password must be at least 8 characters long.")
    if len(value) > 128:
        raise HttpError(400, "Password is too long.")


@router.get("/roles/list", auth=AuthBearer())
def auth_roles(request):
    roles = Role.objects.filter(is_active=True).values("id", "name")
    return list(roles)