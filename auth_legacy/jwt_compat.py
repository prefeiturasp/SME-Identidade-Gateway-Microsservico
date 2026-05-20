"""Mint short-lived JWTs in the legacy CoreSSO/API-EOL shape.

The legacy systems consume JWTs whose payload mimics the fields produced by
the .NET API. We sign them with a service-local HMAC secret so legacy systems
can validate them against the gateway without talking to Keycloak.
"""
from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import jwt
from django.conf import settings


def encode_legacy_token(payload: dict[str, Any]) -> tuple[str, int]:
    now = int(time.time())
    ttl = settings.LEGACY_JWT_TTL
    full = {
        "iss": settings.LEGACY_JWT_ISSUER,
        "iat": now,
        "exp": now + ttl,
        "jti": str(uuid4()),
        **payload,
    }
    token = jwt.encode(full, settings.LEGACY_JWT_SECRET, algorithm="HS256")
    return token, ttl


def decode_legacy_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.LEGACY_JWT_SECRET,
        algorithms=["HS256"],
        issuer=settings.LEGACY_JWT_ISSUER,
    )
