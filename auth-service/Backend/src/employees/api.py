from datetime import date
from typing import Optional

from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel

from common.crud import make_crud_router
from permissions.decorators import require_permission

from .models import CompanyProfile, Department, Designation, Employee, ProductionLine

from authentication.api import AuthBearer

router = Router(tags=["organization"])
company_router = Router(tags=["company-profile"])


# ---------------------------------------------------------------- company profile
class CompanyIn(BaseModel):
    company_name: str
    factory_name: str = ""
    address: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    registration_no: str = ""
    ntn: str = ""
    gst: str = ""
    fiscal_year_start_month: int = 1
    description: str = ""


@company_router.get("", auth=AuthBearer())
@require_permission("ams.company_profile.view")
def get_company(request):
    obj = CompanyProfile.objects.first()
    if obj is None:
        return None
    return _company_dict(obj)


@company_router.put("", auth=AuthBearer())
@require_permission("ams.company_profile.edit")
def upsert_company(request, payload: CompanyIn):
    data = payload.model_dump(exclude_unset=True)
    obj = CompanyProfile.objects.first()
    if obj is None:
        obj = CompanyProfile.objects.create(**data)
    else:
        for key, value in data.items():
            setattr(obj, key, value)
        obj.save()
    return _company_dict(obj)


def _company_dict(o: Optional[CompanyProfile]):
    if o is None:
        return None
    return {
        "id": o.id,
        "company_name": o.company_name,
        "factory_name": o.factory_name,
        "address": o.address,
        "city": o.city,
        "phone": o.phone,
        "email": o.email,
        "website": o.website,
        "registration_no": o.registration_no,
        "ntn": o.ntn,
        "gst": o.gst,
        "fiscal_year_start_month": o.fiscal_year_start_month,
        "description": o.description,
    }


# ---------------------------------------------------------------- department
class DepartmentIn(BaseModel):
    code: str
    name: str
    parent_id: Optional[int] = None
    description: str = ""
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


def department_dict(o: Department) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "parent_id": o.parent_id,
        "parent_name": o.parent.name if o.parent_id else None,
        "description": o.description,
        "is_active": o.is_active,
    }


department_router = make_crud_router(
    entity="department",
    model=Department,
    serializer=department_dict,
    permission="department",
    create_schema=DepartmentIn,
    update_schema=DepartmentUpdate,
    fk_assignable=("parent",),
    search_fields=("name", "code"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- designation
class DesignationIn(BaseModel):
    code: str
    name: str
    department_id: Optional[int] = None
    is_active: bool = True


class DesignationUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


def designation_dict(o: Designation) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "department_id": o.department_id,
        "department_name": o.department.name if o.department_id else None,
        "is_active": o.is_active,
    }


designation_router = make_crud_router(
    entity="designation",
    model=Designation,
    serializer=designation_dict,
    permission="designation",
    create_schema=DesignationIn,
    update_schema=DesignationUpdate,
    fk_assignable=("department",),
    search_fields=("name", "code"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- production line
class LineIn(BaseModel):
    code: str
    name: str
    floor: str = ""
    capacity_pcs: int = 0
    supervisor_id: Optional[int] = None
    is_active: bool = True


class LineUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    floor: Optional[str] = None
    capacity_pcs: Optional[int] = None
    supervisor_id: Optional[int] = None
    is_active: Optional[bool] = None


def line_dict(o: ProductionLine) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "name": o.name,
        "floor": o.floor,
        "capacity_pcs": o.capacity_pcs,
        "supervisor_id": o.supervisor_id,
        "supervisor_name": o.supervisor.full_name if o.supervisor_id else None,
        "is_active": o.is_active,
    }


line_router = make_crud_router(
    entity="production_line",
    model=ProductionLine,
    serializer=line_dict,
    permission="production_line",
    create_schema=LineIn,
    update_schema=LineUpdate,
    fk_assignable=("supervisor",),
    search_fields=("name", "code"),
    uppercase_fields=("code",),
)


# ---------------------------------------------------------------- employee
class EmployeeIn(BaseModel):
    employee_code: Optional[str] = None
    full_name: str
    cnic: Optional[str] = None
    personal_phone: str = ""
    email: Optional[str] = None
    gender: str = ""
    date_of_birth: Optional[date] = None
    department_id: int
    designation_id: int
    joining_date: Optional[date] = None
    reporting_manager_id: Optional[int] = None
    employment_type: str = "permanent"
    is_active: bool = True


class EmployeeUpdate(BaseModel):
    employee_code: Optional[str] = None
    full_name: Optional[str] = None
    cnic: Optional[str] = None
    personal_phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    joining_date: Optional[date] = None
    reporting_manager_id: Optional[int] = None
    employment_type: Optional[str] = None
    is_active: Optional[bool] = None


def employee_dict(o: Employee) -> dict:
    return {
        "id": o.id,
        "employee_code": o.employee_code,
        "full_name": o.full_name,
        "cnic": o.cnic,
        "personal_phone": o.personal_phone,
        "email": o.email,
        "gender": o.gender,
        "date_of_birth": o.date_of_birth.isoformat() if o.date_of_birth else None,
        "department_id": o.department_id,
        "department_name": o.department.name if o.department_id else None,
        "designation_id": o.designation_id,
        "designation_name": o.designation.name if o.designation_id else None,
        "joining_date": o.joining_date.isoformat() if o.joining_date else None,
        "reporting_manager_id": o.reporting_manager_id,
        "reporting_manager_name": o.reporting_manager.full_name if o.reporting_manager_id else None,
        "employment_type": o.employment_type,
        "is_active": o.is_active,
    }


def _next_employee_code() -> str:
    last = Employee.objects.order_by("-id").first()
    seq = (last.id + 1) if last else 1
    while Employee.objects.filter(employee_code=f"EMP-{seq:04d}").exists():
        seq += 1
    return f"EMP-{seq:04d}"


def _clean_cnic(value: Optional[str]):
    if not value:
        return None
    cleaned = str(value).replace("-", "").replace(" ", "").strip()
    return cleaned or None


def _validate_employee(data: dict):
    data["cnic"] = _clean_cnic(data.get("cnic"))
    if data.get("cnic") and Employee.objects.filter(cnic=data["cnic"]).exists():
        raise HttpError(400, "An employee with this CNIC already exists.")
    if data.get("employee_code"):
        data["employee_code"] = str(data["employee_code"]).strip().upper()
        if Employee.objects.filter(employee_code=data["employee_code"]).exists():
            raise HttpError(400, "An employee with this code already exists.")
    else:
        data["employee_code"] = _next_employee_code()


@router.get("", auth=AuthBearer())
@require_permission("ams.employee.view")
def list_employees(
    request,
    search: str = "",
    department_id: Optional[int] = None,
    designation_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
):
    from django.db.models import Q

    qs = Employee.objects.select_related("department", "designation", "reporting_manager").all()
    if search:
        qs = qs.filter(
            Q(full_name__icontains=search) | Q(employee_code__icontains=search) | Q(cnic__icontains=search)
        )
    if department_id is not None:
        qs = qs.filter(department_id=department_id)
    if designation_id is not None:
        qs = qs.filter(designation_id=designation_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    total = qs.count()
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    items = [employee_dict(o) for o in qs.order_by("full_name")[(page - 1) * page_size : page * page_size]]
    return {
        "items": items,
        "pagination": {"page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size if total else 0},
    }


@router.get("/{pk}", auth=AuthBearer())
@require_permission("ams.employee.view")
def get_employee(request, pk: int):
    try:
        obj = Employee.objects.select_related("department", "designation", "reporting_manager").get(pk=pk)
    except Employee.DoesNotExist:
        raise HttpError(404, "Employee not found.")
    return employee_dict(obj)


@router.post("", auth=AuthBearer())
@require_permission("ams.employee.create")
def create_employee(request, payload: EmployeeIn):
    data = payload.model_dump(exclude_unset=True, exclude={"id"})
    _validate_employee(data)
    data["department_id"] = data.pop("department_id")
    data["designation_id"] = data.pop("designation_id")
    if not data.get("joining_date"):
        data["joining_date"] = date.today()
    obj = Employee.objects.create(**data)
    return employee_dict(obj)


@router.patch("/{pk}", auth=AuthBearer())
@require_permission("ams.employee.edit")
def update_employee(request, pk: int, payload: EmployeeUpdate):
    try:
        obj = Employee.objects.select_related("department", "designation").get(pk=pk)
    except Employee.DoesNotExist:
        raise HttpError(404, "Employee not found.")
    data = payload.model_dump(exclude_unset=True, exclude={"id"})
    if "cnic" in data:
        cnic = _clean_cnic(data["cnic"])
        if cnic and Employee.objects.filter(cnic=cnic).exclude(pk=pk).exists():
            raise HttpError(400, "An employee with this CNIC already exists.")
        data["cnic"] = cnic
    if "employee_code" in data and data["employee_code"]:
        data["employee_code"] = str(data["employee_code"]).strip().upper()
    if "department_id" in data:
        data["department_id"] = data.pop("department_id")
    if "designation_id" in data:
        data["designation_id"] = data.pop("designation_id")
    for key, value in data.items():
        setattr(obj, key, value)
    obj.save()
    return employee_dict(obj)


@router.delete("/{pk}", auth=AuthBearer())
@require_permission("ams.employee.delete")
def delete_employee(request, pk: int):
    from audit.middleware import get_client_ip, get_current_user
    from audit.models import record

    try:
        obj = Employee.objects.get(pk=pk)
    except Employee.DoesNotExist:
        raise HttpError(404, "Employee not found.")
    obj.soft_delete(user=get_current_user())
    record("delete", "employees.employee", pk, str(obj), actor=get_current_user(), ip=get_client_ip())
    return {"detail": "Deleted."}