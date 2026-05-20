"""Settings overrides for the pytest suite."""
from gateway_ms.settings import *  # noqa: F401,F403

DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "gateway-ms-tests",
    }
}
AUDIT_PUBLISH_ENABLED = False
KEYCLOAK_VERIFY_SSL = False
LEGACY_JWT_SECRET = "test-legacy-secret"
LEGACY_JWT_ISSUER = "gateway-ms-test"
