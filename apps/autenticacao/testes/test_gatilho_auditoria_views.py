"""Testes de resiliência das views ao gatilho de auditoria.

O disparo do gatilho acontece dentro de fluxos que o usuário está
esperando. Estes testes fixam o contrato de que um destino fora do ar
não muda nada do que o usuário recebe — nem status, nem corpo.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

_KEYCLOAK_ADMIN_VIEWS = "apps.autenticacao.api.views.keycloak_admin"
_KEYCLOAK_ADMIN_CREDENCIAIS = (
    "apps.autenticacao.api.views_credenciais.keycloak_admin"
)
_KEYCLOAK_ADMIN_GATILHO = "apps.autenticacao.gatilho_auditoria.keycloak_admin"
_CLIENTE_TOKEN_MS = "apps.autenticacao.api.views.cliente_token_ms"
_CLIENTE_AUDIT_MS = "apps.autenticacao.gatilho_auditoria.cliente_audit_ms"

_CONTA_KEYCLOAK = {
    "kc_user_id": "5c29cc47-0000-0000-0000-000000000000",
    "username": "1234567",
    "nome": "FULANO DE TAL",
    "email": "fulano@sme.sp.gov.br",
    "ativo": True,
    "cpf": "12345678900",
    "rf": "1234567",
}


def _cliente_audit_indisponivel() -> MagicMock:
    """Cliente do Audit-MS que sempre falha por indisponibilidade."""
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.post.side_effect = httpx.ConnectError("audit-ms fora do ar")
    return cliente


def _cliente_token_ms_indisponivel() -> MagicMock:
    """Cliente do Token-MS que falha — isola o efeito do gatilho."""
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.post.side_effect = httpx.ConnectError("token-ms fora do ar")
    return cliente


class TestResilienciaAoGatilhoDeAuditoria:
    """Garante que o gatilho nunca degrada a resposta ao usuário."""

    @pytest.fixture(autouse=True)
    def _configura_api_key(self, settings: Any) -> None:
        """Define as chaves usadas no escopo de cada teste."""
        settings.API_KEY = "chave-secreta"
        settings.API_KEY_HEADER = "X-API-Key"
        settings.API_KEY_AUDIT_MS = "chave-audit"
        settings.API_KEY_AUDIT_MS_HEADER = "X-API-Key"
        settings.AUDIT_MS_URL = "http://audit-ms:8000/identidade-auditoria"
        settings.AUDIT_MS_TIMEOUT = 2.0
        settings.KEYCLOAK_REALM = "COTIC"

    def test_login_mantem_200_com_audit_ms_fora_do_ar(self) -> None:
        """Deve concluir o login mesmo sem conseguir avisar a auditoria."""
        resultado = {
            "autenticado": True,
            **_CONTA_KEYCLOAK,
            "roles": {"realm_access": {"roles": ["default-roles-cotic"]}},
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }

        with (
            patch(_KEYCLOAK_ADMIN_VIEWS) as mock_keycloak,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_cliente_token_ms_indisponivel(),
            ),
            patch(
                _CLIENTE_AUDIT_MS,
                return_value=_cliente_audit_indisponivel(),
            ) as mock_audit,
        ):
            mock_keycloak.autenticar.return_value = resultado

            response = APIClient().post(
                reverse("login"),
                data={"login": "1234567", "senha": "x"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["access_token"] == "token-jwt"
        mock_audit.assert_called_once()

    def test_login_avisa_a_auditoria_com_realm_e_usuario(self) -> None:
        """Deve avisar a auditoria com o usuário recém-autenticado."""
        resultado = {
            "autenticado": True,
            **_CONTA_KEYCLOAK,
            "roles": {"realm_access": {"roles": []}},
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }
        cliente_audit = MagicMock()
        cliente_audit.__enter__.return_value = cliente_audit
        cliente_audit.post.return_value = httpx.Response(
            202,
            request=httpx.Request("POST", "https://audit-ms/"),
        )

        with (
            patch(_KEYCLOAK_ADMIN_VIEWS) as mock_keycloak,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_cliente_token_ms_indisponivel(),
            ),
            patch(_CLIENTE_AUDIT_MS, return_value=cliente_audit),
        ):
            mock_keycloak.autenticar.return_value = resultado

            APIClient().post(
                reverse("login"),
                data={"login": "1234567", "senha": "x"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        cliente_audit.post.assert_called_once_with(
            "/api/v1/gatilho-poll/",
            json={
                "realm": "COTIC",
                "usuario_id": _CONTA_KEYCLOAK["kc_user_id"],
            },
        )

    def test_alterar_senha_mantem_200_com_audit_ms_fora_do_ar(self) -> None:
        """Deve confirmar a troca de senha mesmo sem avisar a auditoria."""
        admin_gatilho = MagicMock()
        admin_gatilho.obter_dados_usuario.return_value = _CONTA_KEYCLOAK

        with (
            patch(_KEYCLOAK_ADMIN_CREDENCIAIS),
            patch(_KEYCLOAK_ADMIN_GATILHO, admin_gatilho),
            patch(
                _CLIENTE_AUDIT_MS,
                return_value=_cliente_audit_indisponivel(),
            ) as mock_audit,
        ):
            response = APIClient().post(
                reverse("alterar-senha"),
                data={"login": "1234567", "senha": "NovaSenha123"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["situacao"] == "senha_alterada"
        mock_audit.assert_called_once()

    def test_alterar_email_mantem_200_com_audit_ms_fora_do_ar(self) -> None:
        """Deve confirmar a troca de e-mail mesmo sem avisar a auditoria."""
        admin_credenciais = MagicMock()
        admin_credenciais.alterar_email.return_value = {
            "email_alterado": True,
            "verificacao_enviada": True,
        }
        admin_gatilho = MagicMock()
        admin_gatilho.obter_dados_usuario.return_value = _CONTA_KEYCLOAK

        with (
            patch(_KEYCLOAK_ADMIN_CREDENCIAIS, admin_credenciais),
            patch(_KEYCLOAK_ADMIN_GATILHO, admin_gatilho),
            patch(
                _CLIENTE_AUDIT_MS,
                return_value=_cliente_audit_indisponivel(),
            ) as mock_audit,
        ):
            response = APIClient().post(
                reverse("alterar-email"),
                data={"login": "1234567", "email": "novo@sme.sp.gov.br"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["situacao"] == "email_alterado"
        mock_audit.assert_called_once()

    def test_alterar_senha_mantem_204_para_login_inexistente(self) -> None:
        """Deve manter o 204 sem tentar avisar a auditoria."""
        from keycloak.exceptions import KeycloakGetError

        admin_credenciais = MagicMock()
        admin_credenciais.redefinir_senha.side_effect = KeycloakGetError(
            error_message="não encontrado"
        )

        with (
            patch(_KEYCLOAK_ADMIN_CREDENCIAIS, admin_credenciais),
            patch(_CLIENTE_AUDIT_MS) as mock_audit,
        ):
            response = APIClient().post(
                reverse("alterar-senha"),
                data={"login": "0000000", "senha": "NovaSenha123"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_audit.assert_not_called()
