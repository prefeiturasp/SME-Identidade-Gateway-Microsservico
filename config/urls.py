"""Roteamento principal: schema, docs e domínios."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

API_PREFIX = "identidade-gateway/api/v1/"

urlpatterns = [
    path(
        f"{API_PREFIX}schema/",
        SpectacularAPIView.as_view(
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="schema",
    ),
    path(
        f"{API_PREFIX}docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
    path(f"{API_PREFIX}", include("apps.core.api.urls")),
    path(
        f"{API_PREFIX}autenticacao/",
        include("apps.autenticacao.api.urls"),
    ),
    path(
        f"{API_PREFIX}usuarios/",
        include("apps.gestao_usuario.api.urls"),
    ),
]
