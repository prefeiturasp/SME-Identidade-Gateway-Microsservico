"""OIDC bridge endpoints exposed by gateway-ms.

These are thin wrappers around the Keycloak ``openid-connect`` endpoints. The
gateway adds three pieces of value:

* uniform error envelope (so consumers handle a single shape);
* enrichment of access-token claims via token-ms;
* audit hook for every login / logout.

It does **not** replace JWKS-based local validation — applications should keep
validating tokens directly against the Keycloak ``/certs`` endpoint.
"""
from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core import audit, keycloak_client, token_ms_client

from .serializers import (
    IntrospectRequestSerializer,
    LogoutRequestSerializer,
    RefreshRequestSerializer,
    TokenRequestSerializer,
)

logger = logging.getLogger(__name__)


def _error(exc: keycloak_client.KeycloakError) -> Response:
    code = exc.status_code or status.HTTP_502_BAD_GATEWAY
    if code == 401:
        code = status.HTTP_401_UNAUTHORIZED
    return Response(
        {"detail": str(exc), "keycloak": exc.payload},
        status=code,
    )


def _token_payload(token: keycloak_client.TokenResponse, *, enrich_for: str | None) -> dict[str, Any]:
    data = {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "id_token": token.id_token,
        "expires_in": token.expires_in,
        "refresh_expires_in": token.refresh_expires_in,
        "token_type": token.token_type,
        "scope": token.scope,
        "session_state": token.session_state,
    }
    if enrich_for:
        data["claims"] = token_ms_client.fetch_claims(enrich_for)
    return data


@api_view(["POST"])
@permission_classes([AllowAny])
def token(request):
    """Username/password grant — enriquece com claims do token-ms."""
    serializer = TokenRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    v = serializer.validated_data
    try:
        tok = keycloak_client.password_grant(
            v["username"],
            v["password"],
            client_id=v.get("client_id") or None,
            client_secret=v.get("client_secret") or None,
            scope=v.get("scope") or "openid",
        )
    except keycloak_client.KeycloakError as exc:
        audit.publish(
            "oidc.token.failure",
            {"username": v["username"], "reason": str(exc)},
        )
        return _error(exc)

    audit.publish(
        "oidc.token.success",
        {
            "username": v["username"],
            "client_id": v.get("client_id") or None,
            "session_state": tok.session_state,
        },
    )
    return Response(_token_payload(tok, enrich_for=v["username"]))


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request):
    serializer = RefreshRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    v = serializer.validated_data
    try:
        tok = keycloak_client.refresh_token(
            v["refresh_token"],
            client_id=v.get("client_id") or None,
            client_secret=v.get("client_secret") or None,
        )
    except keycloak_client.KeycloakError as exc:
        return _error(exc)
    return Response(_token_payload(tok, enrich_for=None))


@api_view(["POST"])
@permission_classes([AllowAny])
def introspect(request):
    serializer = IntrospectRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        result = keycloak_client.introspect(serializer.validated_data["token"])
    except keycloak_client.KeycloakError as exc:
        return _error(exc)
    return Response(result)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    serializer = LogoutRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        keycloak_client.logout(serializer.validated_data["refresh_token"])
    except keycloak_client.KeycloakError as exc:
        return _error(exc)
    audit.publish("oidc.logout", {"ip": request.META.get("REMOTE_ADDR")})
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def well_known(_request):
    try:
        return Response(keycloak_client.well_known())
    except keycloak_client.KeycloakError as exc:
        return _error(exc)


@api_view(["GET"])
@permission_classes([AllowAny])
def jwks(_request):
    try:
        return Response(keycloak_client.jwks())
    except keycloak_client.KeycloakError as exc:
        return _error(exc)
