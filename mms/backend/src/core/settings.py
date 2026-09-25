"""Django settings for the MMS (Merchandising Management System) service.

Single factory ERP — NOT multi-tenant. Identity, permissions and master data
belong to the central AMS service; this service only stores MMS domain tables
(styles, orders, BOM, costing, samples). References to AMS masters (buyer,
item, color, size, currency, …) are stored as integer AMS ids plus small
denormalized display snapshots.
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent  # .../src
PROJECT_ROOT = BASE_DIR.parent  # .../Backend

# ---- Core ---------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-mms-local-dev-key")
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")
DEPLOY_ENV = os.environ.get("DEPLOY_ENV", "local")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "common",
    "styles",
    "orders",
    "bom",
    "costing",
    "samples",
    "reports",
    "seeds",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---- Database -----------------------------------------------------------
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() in ("1", "true", "yes")
if USE_SQLITE or not os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_PATH", str(PROJECT_ROOT / "db.sqlite3")),
        }
    }
else:
    DATABASES = {"default": dj_database_url.config()}

# ---- MMS service identity -----------------------------------------------
# AMS is the single authority for login, sessions and permissions.
AMS_API_URL = os.environ.get("AMS_API_URL", "http://127.0.0.1:8000/api")
AMS_USER_CACHE_SECONDS = int(os.environ.get("AMS_USER_CACHE_SECONDS", "60"))
AMS_MASTER_CACHE_SECONDS = int(os.environ.get("AMS_MASTER_CACHE_SECONDS", "300"))
AUDIT_REQUIRED = os.environ.get("AUDIT_REQUIRED", "false").lower() in ("1", "true", "yes")
# Retry/fallback creds used by the dev demo seed to prepare AMS masters.
AMS_SEED_USERNAME = os.environ.get("AMS_SEED_USERNAME", "admin")
AMS_SEED_PASSWORD = os.environ.get("AMS_SEED_PASSWORD", "SuperAdmin@123")

# ---- CORS ---------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL_ORIGINS", "true").lower() in ("1", "true", "yes")

# ---- Security / Static / Media -------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(PROJECT_ROOT / "media"))

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() in ("1", "true", "yes")
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() in ("1", "true", "yes")
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

# ---- Ninja API ----------------------------------------------------------
NINJA_PAGINATION_CLASS = None  # manual, uniform shape

TZ = os.environ.get("TZ", "Asia/Karachi")
TIME_ZONE = TZ
USE_TZ = True
LANGUAGE_CODE = "en-us"
USE_I18N = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}