"""Client Credentials proxy used for service-to-service (M2M) calls.

Wrappers a redação do grant ``client_credentials`` no Keycloak. Mantém um
cache curto (default 4 min) por par ``(client_id, scope, audience)`` para que
os sistemas chamadores não precisem implementar lógica de cache local.
"""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core import audit, keycloak_client

logger = logging.getLogger(__name__)


CACHE_PREFIX = "gateway:m2m:"
CACHE_SAFETY_MARGIN = 60  # nunca cachear até a expiração final


class M2MTokenSerializer(serializers.Serializer):
    client_id = serializers.CharField(max_length=255)
    client_secret = serializers.CharField(max_length=512, trim_whitespace=False)
    scope = serializers.CharField(max_length=255, required=False, allow_blank=True)
    audience = serializers.CharField(max_length=255, required=False, allow_blank=True)


def _cache_key(client_id: str, scope: str, audience: str) -> str:
    digest = hashlib.sha256(f"{client_id}|{scope}|{audience}".encode()).hexdigest()
    return f"{CACHE_PREFIX}{digest}"


@api_view(["POST"])
@permission_classes([AllowAny])
def issue_token(request):
    serializer = M2MTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    v = serializer.validated_data

    scope = v.get("scope") or ""
    audience = v.get("audience") or ""
    key = _cache_key(v["client_id"], scope, audience)
    cached = cache.get(key)
    if cached:
        return Response({**cached, "cached": True})

    try:
        tok = keycloak_client.client_credentials(
            v["client_id"],
            v["client_secret"],
            scope=scope or None,
            audience=audience or None,
        )
    except keycloak_client.KeycloakError as exc:
        audit.publish(
            "m2m.token.failure",
            {"client_id": v["client_id"], "reason": str(exc)},
        )
        return Response(
            {"detail": str(exc), "keycloak": exc.payload},
            status=exc.status_code or status.HTTP_502_BAD_GATEWAY,
        )

    payload = {
        "access_token": tok.access_token,
        "token_type": tok.token_type,
        "expires_in": tok.expires_in,
        "scope": tok.scope,
    }
    ttl = max(tok.expires_in - CACHE_SAFETY_MARGIN, 1)
    cache.set(key, payload, ttl)
    audit.publish(
        "m2m.token.success",
        {"client_id": v["client_id"], "scope": scope, "audience": audience},
    )
    return Response({**payload, "cached": False})


class IntrospectInputSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=8192, trim_whitespace=False)
    client_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    client_secret = serializers.CharField(
        max_length=512, required=False, allow_blank=True, trim_whitespace=False
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def introspect(request):
    serializer = IntrospectInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    v = serializer.validated_data
    try:
        data = keycloak_client.introspect(
            v["token"],
            client_id=v.get("client_id") or None,
            client_secret=v.get("client_secret") or None,
        )
    except keycloak_client.KeycloakError as exc:
        return Response(
            {"detail": str(exc), "keycloak": exc.payload},
            status=exc.status_code or status.HTTP_502_BAD_GATEWAY,
        )
    return Response(data)
