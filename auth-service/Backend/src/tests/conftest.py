import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("DEBUG", "true")

import django

django.setup()

import pytest
from django.test import Client

from authentication.models import User
from authentication.rate_limit import limiter
from employees.models import Department, Designation, Employee
from permissions.models import Permission, Role, RolePermission

PASSWORD = "TestPass@123"


@pytest.fixture(autouse=True)
def _reset_limiters():
    limiter.clear()
    yield
    limiter.clear()


@pytest.fixture
def dept(db):
    return Department.objects.create(code="QA", name="Quality Assurance")


@pytest.fixture
def designation(db):
    return Designation.objects.create(code="DEV", name="Developer")


@pytest.fixture
def employee(db, dept, designation):
    return Employee.objects.create(
        employee_code="EMP-0009",
        full_name="QA Tester",
        cnic="2222222222222",
        department=dept,
        designation=designation,
    )


@pytest.fixture
def user(db, employee):
    u = User(username="tester", email="tester@fct.local", is_active=True, employee=employee)
    u.set_password(PASSWORD)
    u.save()
    return u


def make_super_admin(db, employee):
    u = User(username="root", email="root@fct.local", is_active=True, is_super_admin=True, employee=employee)
    u.set_password(PASSWORD)
    u.save()
    return u


def make_permission(db, entity="buyer", action="view"):
    from permissions.models import Service

    service, _ = Service.objects.get_or_create(code="ams", defaults={"name": "Admin & Master System"})
    codename = f"ams.{entity}.{action}"
    perm, _ = Permission.objects.get_or_create(
        codename=codename,
        defaults={"module": service, "entity": entity, "action": action, "name": f"{entity} {action}"},
    )
    return perm


@pytest.fixture
def buyer_view_perm(db):
    return make_permission(db, "buyer", "view")


@pytest.fixture
def role_with_buyer_view(db, buyer_view_perm):
    role = Role.objects.create(name="Buyer Viewer", description="", is_active=True)
    RolePermission.objects.create(role=role, permission=buyer_view_perm)
    return role


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def auth_client(client, employee):
    su = make_super_admin(None, employee)
    res = client.post(
        "/api/auth/login",
        data={"identifier": "root", "password": PASSWORD},
        content_type="application/json",
    )
    assert res.status_code == 200, res.content
    token = res.json()["access_token"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return {"client": client, "user": su}


def login(client, identifier, password):
    return client.post(
        "/api/auth/login",
        data={"identifier": identifier, "password": password},
        content_type="application/json",
    )