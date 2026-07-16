"""Testes das views de gestão de credencial (senha e e-mail)."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from keycloak.exceptions import KeycloakGetError
from rest_framework import status
from rest_framework.test import APIClient


class TestGestaoCredencialEndpoints:
    """Testes de autenticação e comportamento das rotas de credencial."""

    @pytest.fixture(autouse=True)
    def _configura_api_key(self, settings: Any) -> None:
        """Define API_KEY/API_KEY_HEADER para o escopo de cada teste."""
        settings.API_KEY = "chave-secreta"
        settings.API_KEY_HEADER = "X-API-Key"

    def test_recuperar_senha_sem_api_key_retorna_401(self) -> None:
        """Deve rejeitar requisição sem API Key."""
        response = APIClient().post(
            reverse("recuperar-senha"),
            data={"login": "1234567"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("apps.autenticacao.api.views_credenciais.keycloak_admin")
    def test_recuperar_senha_com_sucesso(
        self, mock_keycloak_admin: MagicMock
    ) -> None:
        """Deve confirmar o disparo da recuperação de senha."""
        response = APIClient().post(
            reverse("recuperar-senha"),
            data={"login": "1234567"},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["situacao"] == "solicitacao_enviada"
        mock_keycloak_admin.disparar_redefinicao_senha.assert_called_once_with(
            "1234567"
        )

    @patch("apps.autenticacao.api.views_credenciais.keycloak_admin")
    def test_recuperar_senha_usuario_inexistente_retorna_404(
        self, mock_keycloak_admin: MagicMock
    ) -> None:
        """Deve retornar 404 quando o login não existir no Keycloak."""
        mock_keycloak_admin.disparar_redefinicao_senha.side_effect = (
            KeycloakGetError(error_message="não encontrado")
        )

        response = APIClient().post(
            reverse("recuperar-senha"),
            data={"login": "0000000"},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.autenticacao.api.views_credenciais.keycloak_admin")
    def test_alterar_senha_com_sucesso(
        self, mock_keycloak_admin: MagicMock
    ) -> None:
        """Deve confirmar a alteração de senha temporária."""
        response = APIClient().post(
            reverse("alterar-senha"),
            data={"login": "1234567", "senha": "novaSenha123"},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["situacao"] == "senha_alterada"
        mock_keycloak_admin.redefinir_senha_temporaria.assert_called_once_with(
            "1234567", "novaSenha123"
        )

    @patch("apps.autenticacao.api.views_credenciais.keycloak_admin")
    def test_alterar_senha_usuario_inexistente_retorna_404(
        self, mock_keycloak_admin: MagicMock
    ) -> None:
        """Deve retornar 404 quando o login não existir no Keycloak."""
        mock_keycloak_admin.redefinir_senha_temporaria.side_effect = (
            KeycloakGetError(error_message="não encontrado")
        )

        response = APIClient().post(
            reverse("alterar-senha"),
            data={"login": "0000000", "senha": "x"},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.autenticacao.api.views_credenciais.keycloak_admin")
    def test_alterar_email_com_sucesso(
        self, mock_keycloak_admin: MagicMock
    ) -> None:
        """Deve confirmar a alteração de e-mail."""
        response = APIClient().post(
            reverse("alterar-email"),
            data={"login": "1234567", "email": "novo@sme.sp.gov.br"},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["situacao"] == "email_alterado"
        mock_keycloak_admin.alterar_email.assert_called_once_with(
            "1234567", "novo@sme.sp.gov.br"
        )

    @patch("apps.autenticacao.api.views_credenciais.keycloak_admin")
    def test_alterar_email_usuario_inexistente_retorna_404(
        self, mock_keycloak_admin: MagicMock
    ) -> None:
        """Deve retornar 404 quando o login não existir no Keycloak."""
        mock_keycloak_admin.alterar_email.side_effect = KeycloakGetError(
            error_message="não encontrado"
        )

        response = APIClient().post(
            reverse("alterar-email"),
            data={"login": "0000000", "email": "novo@sme.sp.gov.br"},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_alterar_email_com_email_invalido_retorna_400(self) -> None:
        """Deve rejeitar payload com e-mail em formato inválido."""
        response = APIClient().post(
            reverse("alterar-email"),
            data={"login": "1234567", "email": "nao-e-email"},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
