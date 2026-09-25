"""Django settings for the FCT ERP central auth + AMS backend.

Single factory ERP — NOT multi-tenant. Env-driven with safe local defaults.
DEBUG defaults to OFF; use an env var to enable it for local development.
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent  # .../Backend/src
PROJECT_ROOT = BASE_DIR.parent  # .../Backend

# ---- Core ---------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-fct-erp-local-dev-key")
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
    "authentication",
    "permissions",
    "employees",
    "masters",
    "audit",
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
    "audit.middleware.AuditMiddleware",
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
# Local/SQLite by default; set DATABASE_URL (or AUTH_DATABASE_URL) for Postgres.
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() in ("1", "true", "yes")
if USE_SQLITE or not os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_PATH", str(PROJECT_ROOT / "db.sqlite3")),
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=os.environ.get("DATABASE_URL", os.environ.get("AUTH_DATABASE_URL"))
        )
    }

# ---- Auth ---------------------------------------------------------------
AUTH_USER_MODEL = "authentication.User"
AUTHENTICATION_BACKENDS = []  # no django.contrib.auth login — JWT only

ACCESS_TOKEN_EXPIRY_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRY_HOURS", "1"))
REFRESH_TOKEN_EXPIRY_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRY_DAYS", "7"))
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "RS256")
JWT_PRIVATE_KEY_PATH = os.environ.get("JWT_PRIVATE_KEY_PATH", "")
JWT_PUBLIC_KEY_PATH = os.environ.get("JWT_PUBLIC_KEY_PATH", "")
JWT_KEY_ID = os.environ.get("JWT_KEY_ID", "fct-erp-1")

LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("LOGIN_RATE_LIMIT_ATTEMPTS", "15"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60"))
MAX_FAILED_LOGINS = int(os.environ.get("MAX_FAILED_LOGINS", "5"))
ACCOUNT_LOCKOUT_MINUTES = int(os.environ.get("ACCOUNT_LOCKOUT_MINUTES", "30"))

# ---- Redis (optional; rate limit + perms cache fall back to in-process) --
REDIS_URL = os.environ.get("REDIS_URL", os.environ.get("AUTH_REDIS_URL", ""))

# ---- CORS ---------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL_ORIGINS", "true").lower() in ("1", "true", "yes")

# ---- Security / Static ---------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() in ("1", "true", "yes")
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() in ("1", "true", "yes")
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

# ---- Ninja API ----------------------------------------------------------
NINJA_PAGINATION_CLASS = None  # we paginate manually with a uniform shape

TZ = os.environ.get("TZ", "Asia/Karachi")
TIME_ZONE = TZ
USE_TZ = True
LANGUAGE_CODE = "en-us"
USE_I18N = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}