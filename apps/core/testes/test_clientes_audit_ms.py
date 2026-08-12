"""Testes do cliente HTTP do Audit-MS."""

from typing import Any

import pytest

from apps.core.clientes.audit_ms import cliente_audit_ms


class TestClienteAuditMs:
    """Testes de ``cliente_audit_ms``."""

    def test_inclui_api_key_de_servico_como_header_padrao(
        self, settings: Any
    ) -> None:
        """Deve carregar a API Key de serviço do Gateway por padrão."""
        settings.API_KEY_AUDIT_MS = "chave-de-teste"
        settings.API_KEY_AUDIT_MS_HEADER = "X-API-Key"

        with cliente_audit_ms() as cliente:
            request = cliente.build_request("GET", "/qualquer/")

        assert request.headers["x-api-key"] == "chave-de-teste"

    def test_usa_url_base_e_timeout_configurados(self, settings: Any) -> None:
        """Deve usar AUDIT_MS_URL/AUDIT_MS_TIMEOUT do settings."""
        settings.AUDIT_MS_URL = "https://audit-ms-teste:9000"
        settings.AUDIT_MS_TIMEOUT = 2.5

        with cliente_audit_ms() as cliente:
            assert str(cliente.base_url) == "https://audit-ms-teste:9000"
            assert cliente.timeout.connect == pytest.approx(2.5)
