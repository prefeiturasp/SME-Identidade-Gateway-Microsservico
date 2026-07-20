"""Testes do cliente HTTP do ETL."""

from typing import Any

from apps.gestao_usuario.cliente_etl import cliente_etl


class TestClienteEtl:
    """Testes de ``cliente_etl``."""

    def test_inclui_api_key_de_servico_como_header_padrao(
        self, settings: Any
    ) -> None:
        """Deve carregar a API Key de serviço do Gateway por padrão."""
        settings.API_KEY_ETL = "chave-de-teste"
        settings.API_KEY_ETL_HEADER = "X-API-Key"

        with cliente_etl() as cliente:
            request = cliente.build_request("GET", "/qualquer/")

        assert request.headers["x-api-key"] == "chave-de-teste"

    def test_usa_url_base_e_timeout_configurados(self, settings: Any) -> None:
        """Deve usar ETL_URL/ETL_TIMEOUT do settings."""
        settings.ETL_URL = "http://etl-teste:9000"
        settings.ETL_TIMEOUT = 12.5

        with cliente_etl() as cliente:
            assert str(cliente.base_url) == "http://etl-teste:9000"
            assert cliente.timeout.connect == 12.5
