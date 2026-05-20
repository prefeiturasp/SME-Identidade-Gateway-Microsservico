"""Django settings for gateway-ms (SME-Identidade)."""
from __future__ import annotations

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-change-in-production-gateway-ms-key"
)

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "core.apps.CoreConfig",
    "auth_oidc.apps.AuthOidcConfig",
    "auth_legacy.apps.AuthLegacyConfig",
    "m2m.apps.M2MConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gateway_ms.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "gateway_ms.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default="postgres://gateway:gateway@localhost:5435/gateway_db",
        conn_max_age=600,
        conn_health_checks=True,
    ),
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("CACHE_URL", "redis://localhost:6380/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Gateway-MS API — SME Identidade",
    "DESCRIPTION": "Microsserviço de autenticação (OIDC + Legado + M2M).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

_cors_raw = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
CORS_ALLOW_ALL_ORIGINS = DEBUG or "*" in _cors_raw
CORS_ALLOWED_ORIGINS = [] if CORS_ALLOW_ALL_ORIGINS else _cors_raw

# --- Keycloak ---------------------------------------------------------------
KEYCLOAK_SERVER_URL = os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8080/")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "sme-apps")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "gateway-ms")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
KEYCLOAK_VERIFY_SSL = os.environ.get("KEYCLOAK_VERIFY_SSL", "true").lower() == "true"
KEYCLOAK_TIMEOUT = int(os.environ.get("KEYCLOAK_TIMEOUT", "10"))

# --- Token-MS ---------------------------------------------------------------
TOKEN_MS_URL = os.environ.get("TOKEN_MS_URL", "http://token-ms-api:8003")
TOKEN_MS_INTERNAL_TOKEN = os.environ.get("TOKEN_MS_INTERNAL_TOKEN", "")
TOKEN_MS_TIMEOUT = int(os.environ.get("TOKEN_MS_TIMEOUT", "15"))

# --- Legado (JWT compat) ----------------------------------------------------
LEGACY_JWT_ISSUER = os.environ.get(
    "LEGACY_JWT_ISSUER", "sme-identidade-gateway-legacy"
)
LEGACY_JWT_SECRET = os.environ.get(
    "LEGACY_JWT_SECRET", SECRET_KEY
)
LEGACY_JWT_TTL = int(os.environ.get("LEGACY_JWT_TTL", "3600"))

# --- Auditoria / Eventos ----------------------------------------------------
RABBITMQ_URL = os.environ.get(
    "RABBITMQ_URL", "amqp://identidade:identidade@localhost:5672/sme"
)
AUDIT_EVENT_EXCHANGE = os.environ.get("AUDIT_EVENT_EXCHANGE", "sme.audit")
AUDIT_PUBLISH_ENABLED = (
    os.environ.get("AUDIT_PUBLISH_ENABLED", "false").lower() == "true"
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
