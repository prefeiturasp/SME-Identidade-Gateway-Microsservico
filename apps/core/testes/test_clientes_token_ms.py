"""Testes do cliente HTTP do Token-MS."""

from typing import Any

import pytest

from apps.core.clientes.token_ms import cliente_token_ms


class TestClienteTokenMs:
    """Testes de ``cliente_token_ms``."""

    def test_inclui_api_key_de_servico_como_header_padrao(
        self, settings: Any
    ) -> None:
        """Deve carregar a API Key de serviço do Gateway por padrão."""
        settings.API_KEY_TOKEN_MS = "chave-de-teste"
        settings.API_KEY_TOKEN_MS_HEADER = "X-API-Key"

        with cliente_token_ms() as cliente:
            request = cliente.build_request("GET", "/qualquer/")

        assert request.headers["x-api-key"] == "chave-de-teste"

    def test_usa_url_base_e_timeout_configurados(self, settings: Any) -> None:
        """Deve usar TOKEN_MS_URL/TOKEN_MS_TIMEOUT do settings."""
        settings.TOKEN_MS_URL = "https://token-ms-teste:9000"
        settings.TOKEN_MS_TIMEOUT = 7.5

        with cliente_token_ms() as cliente:
            assert str(cliente.base_url) == "https://token-ms-teste:9000"
            assert cliente.timeout.connect == pytest.approx(7.5)
