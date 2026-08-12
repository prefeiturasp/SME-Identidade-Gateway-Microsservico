"""Testes do disparo do gatilho de auditoria."""

from unittest.mock import MagicMock, patch

import httpx

from apps.autenticacao.gatilho_auditoria import (
    disparar_gatilho,
    disparar_gatilho_por_login,
)

_CLIENTE = "apps.autenticacao.gatilho_auditoria.cliente_audit_ms"
_KEYCLOAK_ADMIN = "apps.autenticacao.gatilho_auditoria.keycloak_admin"

_USUARIO_ID = "5c29cc47-0000-0000-0000-000000000000"


def _mock_cliente(resposta: httpx.Response | Exception) -> MagicMock:
    """Mock do cliente HTTP do Audit-MS."""
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente

    if isinstance(resposta, Exception):
        cliente.post.side_effect = resposta
    else:
        cliente.post.return_value = resposta

    return cliente


def _resposta(status_code: int) -> httpx.Response:
    """Resposta simulada do endpoint de gatilho."""
    return httpx.Response(
        status_code,
        request=httpx.Request("POST", "https://audit-ms/api/v1/gatilho-poll/"),
    )


class TestDispararGatilho:
    """Testes de ``disparar_gatilho``."""

    def test_envia_apenas_realm_e_usuario(self) -> None:
        """Deve enviar só o aviso mínimo, nunca um evento montado."""
        cliente = _mock_cliente(_resposta(202))

        with patch(_CLIENTE, return_value=cliente):
            resultado = disparar_gatilho("COTIC", _USUARIO_ID)

        assert resultado is True
        cliente.post.assert_called_once_with(
            "/api/v1/gatilho-poll/",
            json={"realm": "COTIC", "usuario_id": _USUARIO_ID},
        )

    def test_nao_dispara_sem_usuario(self) -> None:
        """Deve desistir quando o usuário não é conhecido."""
        cliente = _mock_cliente(_resposta(202))

        with patch(_CLIENTE, return_value=cliente) as fabrica:
            resultado = disparar_gatilho("COTIC", None)

        assert resultado is False
        fabrica.assert_not_called()

    def test_nao_propaga_falha_de_comunicacao(self) -> None:
        """Deve engolir falha de rede em vez de propagá-la."""
        cliente = _mock_cliente(httpx.ConnectError("destino fora do ar"))

        with patch(_CLIENTE, return_value=cliente):
            resultado = disparar_gatilho("COTIC", _USUARIO_ID)

        assert resultado is False

    def test_nao_propaga_timeout(self) -> None:
        """Deve engolir timeout — o disparo é acessório ao fluxo."""
        cliente = _mock_cliente(httpx.ReadTimeout("demorou demais"))

        with patch(_CLIENTE, return_value=cliente):
            resultado = disparar_gatilho("COTIC", _USUARIO_ID)

        assert resultado is False

    def test_considera_recusado_status_diferente_de_202(self) -> None:
        """Deve reportar recusa quando o destino não aceita o aviso."""
        cliente = _mock_cliente(_resposta(400))

        with patch(_CLIENTE, return_value=cliente):
            resultado = disparar_gatilho("COTIC", _USUARIO_ID)

        assert resultado is False


class TestDispararGatilhoPorLogin:
    """Testes de ``disparar_gatilho_por_login``."""

    def test_resolve_conta_e_dispara(self, settings: object) -> None:
        """Deve traduzir o login para o identificador do Keycloak."""
        cliente = _mock_cliente(_resposta(202))
        admin = MagicMock()
        admin.obter_dados_usuario.return_value = {"kc_user_id": _USUARIO_ID}

        with (
            patch(_KEYCLOAK_ADMIN, admin),
            patch(_CLIENTE, return_value=cliente),
        ):
            resultado = disparar_gatilho_por_login("1234567")

        assert resultado is True
        enviado = cliente.post.call_args.kwargs["json"]
        assert enviado["usuario_id"] == _USUARIO_ID

    def test_nao_dispara_quando_login_nao_existe(self) -> None:
        """Deve desistir quando a conta não é encontrada."""
        admin = MagicMock()
        admin.obter_dados_usuario.return_value = None

        with patch(_KEYCLOAK_ADMIN, admin), patch(_CLIENTE) as fabrica:
            resultado = disparar_gatilho_por_login("inexistente")

        assert resultado is False
        fabrica.assert_not_called()

    def test_nao_propaga_falha_na_resolucao_da_conta(self) -> None:
        """Deve engolir falha ao consultar o Keycloak."""
        admin = MagicMock()
        admin.obter_dados_usuario.side_effect = RuntimeError("keycloak fora")

        with patch(_KEYCLOAK_ADMIN, admin), patch(_CLIENTE) as fabrica:
            resultado = disparar_gatilho_por_login("1234567")

        assert resultado is False
        fabrica.assert_not_called()
