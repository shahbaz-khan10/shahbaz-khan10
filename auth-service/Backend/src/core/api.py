from ninja import NinjaAPI

from authentication.api import router as auth_router
from audit.api import router as audit_router
from employees.api import company_router, department_router, designation_router, line_router, router as employee_router
from masters.api import (
    buyer_router,
    color_router,
    currency_router,
    item_category_router,
    item_router,
    router as masters_router,
    size_router,
    supplier_router,
    unit_router,
    uom_conversion_router,
    warehouse_router,
)
from permissions.api import router as rbac_router

api = NinjaAPI(title="FCT ERP - RMS API", version="1.0.0", docs_url="/docs/", description="Authentication, identity & business master APIs for the factory ERP.")

api.add_router("/auth", auth_router)

api.add_router("/audit", audit_router)

api.add_router("/employees", employee_router)
api.add_router("/company", company_router)
api.add_router("/departments", department_router)
api.add_router("/designations", designation_router)
api.add_router("/production-lines", line_router)

api.add_router("/currencies", currency_router)
api.add_router("/buyers", buyer_router)
api.add_router("/suppliers", supplier_router)
api.add_router("/item-categories", item_category_router)
api.add_router("/items", item_router)
api.add_router("/units-of-measure", unit_router)
api.add_router("/uom-conversions", uom_conversion_router)
api.add_router("/colors", color_router)
api.add_router("/sizes", size_router)
api.add_router("/warehouses", warehouse_router)

api.add_router("", masters_router)

api.add_router("", rbac_router)