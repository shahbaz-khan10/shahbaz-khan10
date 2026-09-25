from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from authentication.jwks_view import jwks_view
from .api import api

urlpatterns = [
    path("api/", api.urls),
    path("admin/", admin.site.urls),
    path(".well-known/jwks.json", csrf_exempt(jwks_view), name="jwks"),
]