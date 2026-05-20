"""HTTP client for the token-ms enrichment endpoint."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class TokenMSError(Exception):
    """Raised when token-ms returns a non-2xx response."""


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = getattr(settings, "TOKEN_MS_INTERNAL_TOKEN", "")
    if token:
        headers["X-Internal-Token"] = token
    return headers


def fetch_claims(login: str, *, default: dict | None = None) -> dict[str, Any]:
    """Fetch enrichment claims for ``login`` from token-ms.

    Returns ``default`` (or an empty dict) when the service is unavailable so
    the authentication flow stays usable in degraded mode.
    """
    base = settings.TOKEN_MS_URL.rstrip("/")
    url = f"{base}/api/v1/users/{login}/claims"
    try:
        with httpx.Client(timeout=settings.TOKEN_MS_TIMEOUT) as client:
            resp = client.get(url, headers=_headers())
        if resp.status_code == 404:
            return default if default is not None else {}
        if resp.status_code >= 400:
            raise TokenMSError(f"token-ms {resp.status_code}: {resp.text[:200]}")
        return resp.json() or {}
    except httpx.HTTPError as exc:
        logger.warning("token-ms unreachable: %s", exc)
        return default if default is not None else {}
