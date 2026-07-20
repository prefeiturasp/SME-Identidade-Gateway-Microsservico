"""Testes do cliente HTTP do Token-MS."""

from typing import Any

from apps.core.clientes.token_ms import cliente_token_ms


class TestClienteTokenMs:
    """Testes de ``cliente_token_ms``."""

    def test_inclui_api_key_de_servico_como_header_padrao(self) -> None:
        """Deve carregar a API Key de serviço do Gateway por padrão."""
        with cliente_token_ms() as cliente:
            request = cliente.build_request("GET", "/qualquer/")

        assert "x-api-key" in request.headers
        assert request.headers["x-api-key"] != ""

    def test_usa_url_base_e_timeout_configurados(self, settings: Any) -> None:
        """Deve usar TOKEN_MS_URL/TOKEN_MS_TIMEOUT do settings."""
        settings.TOKEN_MS_URL = "http://token-ms-teste:9000"
        settings.TOKEN_MS_TIMEOUT = 7.5

        with cliente_token_ms() as cliente:
            assert str(cliente.base_url) == "http://token-ms-teste:9000"
            assert cliente.timeout.connect == 7.5
