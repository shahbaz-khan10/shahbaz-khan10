"""MMS API root. Mirrors AMS layout: /api/<app>... with the same pagination
shape and Bearer auth resolved against AMS /auth/me.
"""

from ninja import NinjaAPI

from bom.api import router as bom_router
from costing.api import router as costing_router
from orders.api import router as orders_router
from reports.api import router as reports_router
from samples.api import router as samples_router
from styles.api import router as styles_router

api = NinjaAPI(
    title="MMS API - Merchandising Management System",
    version="1.0.0",
    description="Order, BOM, costing, sample management. Backed by AMS for identity, permissions and masters.",
)

api.add_router("/styles", styles_router)
api.add_router("/orders", orders_router)
api.add_router("/bom", bom_router)
api.add_router("/costing", costing_router)
api.add_router("/samples", samples_router)
api.add_router("/reports", reports_router)


@api.exception_handler(Exception)
def unhandled_exception(request, exc):
    import logging

    logger = logging.getLogger("mms")
    logger.exception("Unhandled error on %s", request.path)
    from ninja.errors import HttpError

    from django.conf import settings as dj_settings

    if isinstance(exc, HttpError):
        return api.create_response(request, {"detail": exc.detail}, status=exc.status_code)
    message = str(exc) or exc.__class__.__name__
    if dj_settings.DEBUG:
        return api.create_response(request, {"detail": f"Internal server error: {message}"}, status=500)
    return api.create_response(request, {"detail": "Internal server error."}, status=500)