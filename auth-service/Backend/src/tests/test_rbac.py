from authentication.models import User
from permissions.models import EmployeeRole

from .conftest import PASSWORD


def login(client, identifier, password):
    return client.post(
        "/api/auth/login",
        data={"identifier": identifier, "password": password},
        content_type="application/json",
    )


def make_user(db, employee, username, is_super_admin=False, roles=(), perms=()):
    u = User(username=username, email=f"{username}@fct.local", is_active=True, is_super_admin=is_super_admin, employee=employee)
    u.set_password(PASSWORD)
    u.save()
    for role in roles:
        EmployeeRole.objects.create(user=u, role=role)
    return u


def bearer(client, user):
    res = login(client, user.username, PASSWORD)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {res.json()['access_token']}"
    return client


class TestAccessControl:
    def test_requires_auth(self, client):
        res = client.get("/api/departments")
        assert res.status_code == 401

    def test_denied_without_permission(self, client, user):
        bearer(client, user)
        res = client.get("/api/departments")
        assert res.status_code == 403

    def test_allowed_with_permission(self, client, employee, dept):
        from .conftest import make_permission
        from permissions.models import Role, RolePermission

        role = Role.objects.create(name="Dept Viewer", is_active=True)
        perm = make_permission(None, "department", "view")
        RolePermission.objects.create(role=role, permission=perm)
        u = make_user(None, employee, "deptviewer", roles=[role])
        bearer(client, u)
        res = client.get("/api/departments")
        assert res.status_code == 200

    def test_super_admin_bypasses(self, client, employee):
        u = make_user(None, employee, "superfix", is_super_admin=True)
        bearer(client, u)
        res = client.get("/api/departments")
        assert res.status_code == 200

    def test_inactive_role_loses_access(self, client, employee):
        from .conftest import make_permission
        from permissions.models import Role, RolePermission

        role = Role.objects.create(name="Temp Viewer", is_active=True)
        RolePermission.objects.create(role=role, permission=make_permission(None, "department", "view"))
        u = make_user(None, employee, "tmpview", roles=[role])
        bearer(client, u)
        assert client.get("/api/departments").status_code == 200
        role.is_active = False
        role.save()
        assert client.get("/api/departments").status_code == 403


class TestUserManagement:
    def test_create_user_requires_employee(self, auth_client):
        res = auth_client["client"].post(
            "/api/users",
            data={"username": "x", "password": "SomePass@123"},
            content_type="application/json",
        )
        assert res.status_code == 422

    def test_create_user_assigns_roles(self, client, employee, role_with_buyer_view, auth_client):
        res = auth_client["client"].post(
            "/api/users",
            data={
                "username": "keeper",
                "password": "Keeper@123",
                "employee_id": employee.id,
                "role_ids": [role_with_buyer_view.id],
            },
            content_type="application/json",
        )
        assert res.status_code == 200
        u = User.objects.get(username="keeper")
        assert u.assigned_roles.count() == 1
        assert u.assigned_roles.first().role_id == role_with_buyer_view.id

        res = login(client, "keeper", "Keeper@123")
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {res.json()['access_token']}"
        assert client.get("/api/buyers").status_code == 200
        assert client.get("/api/departments").status_code == 403

    def test_grant_super_admin_requires_super_admin(self, client, employee, auth_client):
        u = make_user(None, employee, "normal")

        from permissions.models import Role

        role = Role.objects.create(name="Any", is_active=True)
        from .conftest import make_permission

        RolePermission = __import__("permissions.models", fromlist=["RolePermission"]).RolePermission
        RolePermission.objects.create(role=role, permission=make_permission(None, "user", "edit"))
        EmployeeRole.objects.create(user=u, role=role)
        bearer(client, u)

        res = client.patch(
            f"/api/users/{u.id}",
            data={"is_super_admin": True},
            content_type="application/json",
        )
        assert res.status_code == 403


class TestRolePermissions:
    def test_update_role_permissions(self, client, role_with_buyer_view, auth_client, db):
        from .conftest import make_permission

        view_perm = make_permission(None, "user", "view")
        res = auth_client["client"].put(
            f"/api/roles/{role_with_buyer_view.id}/permissions",
            data={"permission_ids": [view_perm.id]},
            content_type="application/json",
        )
        assert res.status_code == 200
        role_with_buyer_view.refresh_from_db()
        ids = list(role_with_buyer_view.role_permissions.values_list("permission_id", flat=True))
        assert ids == [view_perm.id]