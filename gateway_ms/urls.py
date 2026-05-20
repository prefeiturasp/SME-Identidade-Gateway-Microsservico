"""Root URL configuration for gateway-ms."""
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("api/health/", include("core.urls")),
    path("api/v1/oidc/", include("auth_oidc.urls")),
    path("api/v1/", include("auth_legacy.urls")),
    path("api/v1/m2m/", include("m2m.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
