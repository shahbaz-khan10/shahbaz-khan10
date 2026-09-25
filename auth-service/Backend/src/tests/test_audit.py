from .conftest import PASSWORD, make_permission
from audit.models import AuditLog
from authentication.models import User
from permissions.models import EmployeeRole, Role, RolePermission


class TestAuditTrace:
    def test_login_writes_audit(self, client, user):
        res = client.post(
            "/api/auth/login",
            data={"identifier": "tester", "password": PASSWORD},
            content_type="application/json",
        )
        assert res.status_code == 200
        assert AuditLog.objects.filter(entity_type="authentication.user", action="login").exists()

    def test_crud_writes_audit(self, auth_client):
        res = auth_client["client"].post(
            "/api/departments",
            data={"code": "MKT", "name": "Marketing"},
            content_type="application/json",
        )
        assert res.status_code == 200
        row = AuditLog.objects.filter(entity_type="employees.department", action="create").latest("id")
        assert row.actor_user_id is not None

    def test_delete_is_audited(self, auth_client):
        res = auth_client["client"].post(
            "/api/colors",
            data={"code": "PNK", "name": "Pink"},
            content_type="application/json",
        )
        pk = res.json()["id"]
        auth_client["client"].delete(f"/api/colors/{pk}")
        assert AuditLog.objects.filter(entity_type="masters.color", action="delete", entity_id=str(pk)).exists()

    def test_audit_view_requires_permission(self, client, employee, user):
        res = client.post(
            "/api/auth/login",
            data={"identifier": "tester", "password": PASSWORD},
            content_type="application/json",
        )
        token = res.json()["access_token"]
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        res = client.get("/api/audit/logs")
        assert res.status_code == 403

    def test_audit_view_allowed_with_perm(self, client, employee):
        u = User(username="auditor", email="auditor@fct.local", is_active=True, employee=employee)
        u.set_password(PASSWORD)
        u.save()
        role = Role.objects.create(name="Auditor", is_active=True)
        RolePermission.objects.create(role=role, permission=make_permission(None, "audit", "view"))
        EmployeeRole.objects.create(user=u, role=role)
        res = client.post(
            "/api/auth/login",
            data={"identifier": "auditor", "password": PASSWORD},
            content_type="application/json",
        )
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {res.json()['access_token']}"
        res = client.get("/api/audit/logs")
        assert res.status_code == 200
        "items" in res.json()