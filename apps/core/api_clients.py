"""Clientes HTTP das APIs de domínio."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from django.conf import settings

from apps.core.http_client import ServiceClient

DomainName = Literal[
    "token",
    "auditoria",
]

_CLIENTS: dict[DomainName, ServiceClient] = {}


def get_api_client(domain: DomainName) -> ServiceClient:
    """Retorna o cliente HTTP cacheado para a API de um domínio."""
    client = _CLIENTS.get(domain)
    if client is None:
        client = _client_factories()[domain]()
        _CLIENTS[domain] = client
    return client


def close_api_clients() -> None:
    """Fecha todos os clientes HTTP cacheados."""
    for client in _CLIENTS.values():
        client.close()
    _CLIENTS.clear()


def _client_factories() -> dict[DomainName, Callable[[], ServiceClient]]:
    """Monta factories com as configurações atuais do Django."""
    return {
        "token": lambda: ServiceClient(
            base_url=settings.TOKEN_MS_URL,
            dominio="token",
            api_key=settings.API_KEY_TOKEN_MS,
            api_key_header=settings.API_KEY_TOKEN_MS_HEADER,
        ),
        "auditoria": lambda: ServiceClient(
            base_url=settings.AUDIT_MS_URL,
            dominio="auditoria",
            api_key=settings.API_KEY_AUDIT_MS,
            api_key_header=settings.API_KEY_AUDIT_MS_HEADER,
        ),
    }
