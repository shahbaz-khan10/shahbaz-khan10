"""RBAC resolution: does this user hold a permission (directly or via roles)?

Single-factory design: there is no tenant scoping. Super Admin users bypass.
"""

from .models import EmployeeRole, Permission


def user_has_permission(user, codename: str) -> bool:
    if user is None:
        return False
    if user.is_super_admin:
        return True
    return EmployeeRole.objects.filter(
        user_id=user.id, role__is_active=True, role__permissions__codename=codename
    ).exists()


def effective_permissions(user) -> list:
    if user is None:
        return []
    if user.is_super_admin:
        return list(Permission.objects.values_list("codename", flat=True))
    return list(
        EmployeeRole.objects.filter(user_id=user.id, role__is_active=True)
        .values_list("role__permissions__codename", flat=True)
        .distinct()
    )


def roles_for_user(user) -> list:
    if user is None:
        return []
    from .models import EmployeeRole

    names = list(
        EmployeeRole.objects.filter(user_id=user.id, role__is_active=True).values_list("role__name", flat=True)
    )
    if user.is_super_admin and "Super Admin" not in names:
        names.append("Super Admin")
    return names


def has_any_permission(user, codenames) -> bool:
    return any(user_has_permission(user, c) for c in codenames)