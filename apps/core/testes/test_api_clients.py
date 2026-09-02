"""Valida o registry de clientes das APIs de domínio."""

from django.test import SimpleTestCase

from apps.core.api_clients import close_api_clients, get_api_client


class ApiClientsTest(SimpleTestCase):
    """Valida a separação de clientes por domínio."""

    def tearDown(self) -> None:
        close_api_clients()

    def test_reaproveita_cliente_do_mesmo_dominio(self) -> None:
        """Retorna a mesma instância em chamadas repetidas do domínio."""
        primeiro = get_api_client("token")
        segundo = get_api_client("token")

        self.assertIs(primeiro, segundo)

    def test_cria_clientes_distintos_por_dominio(self) -> None:
        """Mantém nomes lógicos separados para circuit breakers."""
        token = get_api_client("token")
        auditoria = get_api_client("auditoria")

        self.assertIsNot(token, auditoria)
        self.assertEqual(token.dominio, "token")
        self.assertEqual(auditoria.dominio, "auditoria")
