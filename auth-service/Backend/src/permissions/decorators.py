from functools import wraps

from ninja.errors import HttpError

from . import rbac


def require_permission(codename: str):
    """Gates an endpoint on a module-wise/action-wise permission.

    `codename` follows the `ams.<entity>.<action>` convention, e.g.
    `ams.item.create`.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "auth", None)
            if not rbac.user_has_permission(user, codename):
                raise HttpError(403, f"You need the '{codename}' permission to do that.")
            return func(request, *args, **kwargs)

        return wrapper

    return decorator