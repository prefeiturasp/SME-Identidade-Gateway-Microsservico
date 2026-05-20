"""Thin HTTP client around Keycloak token + introspection endpoints.

Uses raw HTTP (httpx) instead of python-keycloak admin so the gateway stays
stateless and easily mockable in tests.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class KeycloakError(Exception):
    """Raised when the Keycloak server returns an unexpected error."""

    def __init__(self, message: str, *, status_code: int | None = None,
                 payload: dict | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    refresh_token: str | None
    id_token: str | None
    expires_in: int
    refresh_expires_in: int | None
    token_type: str
    scope: str | None
    session_state: str | None
    raw: dict[str, Any]


def _realm_base(realm: str | None = None) -> str:
    server = settings.KEYCLOAK_SERVER_URL.rstrip("/")
    realm = realm or settings.KEYCLOAK_REALM
    return f"{server}/realms/{realm}"


def _post(url: str, data: dict[str, Any], *, expect_json: bool = True) -> Any:
    try:
        with httpx.Client(
            timeout=settings.KEYCLOAK_TIMEOUT,
            verify=settings.KEYCLOAK_VERIFY_SSL,
        ) as client:
            resp = client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        raise KeycloakError(f"Falha de transporte com Keycloak: {exc}") from exc

    if resp.status_code >= 400:
        try:
            payload = resp.json()
        except ValueError:
            payload = {"raw": resp.text}
        raise KeycloakError(
            payload.get("error_description") or payload.get("error") or "keycloak error",
            status_code=resp.status_code,
            payload=payload,
        )

    if not expect_json or not resp.content:
        return {}
    return resp.json()


def _parse_token(payload: dict[str, Any]) -> TokenResponse:
    return TokenResponse(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        id_token=payload.get("id_token"),
        expires_in=int(payload.get("expires_in", 0)),
        refresh_expires_in=payload.get("refresh_expires_in"),
        token_type=payload.get("token_type", "Bearer"),
        scope=payload.get("scope"),
        session_state=payload.get("session_state"),
        raw=payload,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def password_grant(
    username: str,
    password: str,
    *,
    realm: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    scope: str = "openid",
) -> TokenResponse:
    """Resource Owner Password Credentials Grant.

    Used by the legacy bridge endpoint. Do NOT expose to new clients.
    """
    url = f"{_realm_base(realm)}/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": client_id or settings.KEYCLOAK_CLIENT_ID,
        "username": username,
        "password": password,
        "scope": scope,
    }
    secret = client_secret if client_secret is not None else settings.KEYCLOAK_CLIENT_SECRET
    if secret:
        data["client_secret"] = secret
    return _parse_token(_post(url, data))


def refresh_token(
    refresh: str,
    *,
    realm: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> TokenResponse:
    url = f"{_realm_base(realm)}/protocol/openid-connect/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": client_id or settings.KEYCLOAK_CLIENT_ID,
    }
    secret = client_secret if client_secret is not None else settings.KEYCLOAK_CLIENT_SECRET
    if secret:
        data["client_secret"] = secret
    return _parse_token(_post(url, data))


def client_credentials(
    client_id: str,
    client_secret: str,
    *,
    realm: str | None = None,
    scope: str | None = None,
    audience: str | None = None,
) -> TokenResponse:
    url = f"{_realm_base(realm)}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if scope:
        data["scope"] = scope
    if audience:
        data["audience"] = audience
    return _parse_token(_post(url, data))


def introspect(
    token: str,
    *,
    realm: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict[str, Any]:
    url = f"{_realm_base(realm)}/protocol/openid-connect/token/introspect"
    data = {
        "token": token,
        "client_id": client_id or settings.KEYCLOAK_CLIENT_ID,
    }
    secret = client_secret if client_secret is not None else settings.KEYCLOAK_CLIENT_SECRET
    if secret:
        data["client_secret"] = secret
    return _post(url, data)


def logout(
    refresh: str,
    *,
    realm: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> None:
    url = f"{_realm_base(realm)}/protocol/openid-connect/logout"
    data = {
        "refresh_token": refresh,
        "client_id": client_id or settings.KEYCLOAK_CLIENT_ID,
    }
    secret = client_secret if client_secret is not None else settings.KEYCLOAK_CLIENT_SECRET
    if secret:
        data["client_secret"] = secret
    _post(url, data, expect_json=False)


def well_known(realm: str | None = None) -> dict[str, Any]:
    url = f"{_realm_base(realm)}/.well-known/openid-configuration"
    try:
        with httpx.Client(
            timeout=settings.KEYCLOAK_TIMEOUT,
            verify=settings.KEYCLOAK_VERIFY_SSL,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise KeycloakError(f"Falha ao obter discovery: {exc}") from exc
    return resp.json()


def jwks(realm: str | None = None) -> dict[str, Any]:
    url = f"{_realm_base(realm)}/protocol/openid-connect/certs"
    try:
        with httpx.Client(
            timeout=settings.KEYCLOAK_TIMEOUT,
            verify=settings.KEYCLOAK_VERIFY_SSL,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise KeycloakError(f"Falha ao obter JWKS: {exc}") from exc
    return resp.json()
