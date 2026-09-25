"""Authentication for MMS endpoints.

MMS has no login. Every request presents the same Bearer token issued by AMS;
we resolve it against AMS /auth/me (cached) — the returned payload carries the
user's roles and effective permissions (mms.* included), so AMS remains the
single source of truth for 'who may do what'.
"""

from functools import wraps

from ninja.errors import HttpError
from ninja.security import HttpBearer

from .ams_client import ams


class AuthBearer(HttpBearer):
    def authenticate(self, request, token: str):
        user = ams.whoami(token)
        if not user:
            return None
        request.user_token = token  # for downstream AMS calls
        return user

    def authenticate_header(self, request):
        return "Bearer"


def require_permission(codename: str):
    """Gates an endpoint on an AMS permission, e.g. `mms.order.create`."""

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "auth", None)
            if not user:
                raise HttpError(401, "Authentication required.")
            perms = user.get("perms") or []
            if codename not in perms and not user.get("is_super_admin"):
                raise HttpError(403, f"You need the '{codename}' permission to do that.")
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def actor(request) -> dict:
    """Compact actor snapshot {id, full_name, username} for audit/denorm fields."""
    user = getattr(request, "auth", None)
    if not user:
        return {"id": None, "full_name": "", "username": ""}
    return {
        "id": user.get("id"),
        "full_name": user.get("full_name") or user.get("username", ""),
        "username": user.get("username", ""),
    }


def actor_values(request) -> dict:
    return {"created_by": actor(request).get("id"), "created_by_name": actor(request).get("full_name")}


def request_token(request) -> str:
    return getattr(request, "user_token", "")