"""Testes das views do fluxo de login e níveis de acesso."""

from typing import Any
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

_KEYCLOAK_ADMIN = "apps.autenticacao.api.views.keycloak_admin"


class TestAutenticacaoEndpoints:
    """Testes de autenticação e autorização exigidas pelos endpoints."""

    @pytest.fixture(autouse=True)
    def _configura_api_key(self, settings: Any) -> None:
        """Define API_KEY/API_KEY_HEADER para o escopo de cada teste."""
        settings.API_KEY = "chave-secreta"
        settings.API_KEY_HEADER = "X-API-Key"

    def test_login_sem_api_key_retorna_401(self) -> None:
        """Deve rejeitar requisição sem API Key."""
        response = APIClient().post(
            reverse("login"),
            data={"login": "1234567", "senha": "x"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_com_api_key_invalida_retorna_401(self) -> None:
        """Deve rejeitar requisição com API Key incorreta."""
        response = APIClient().post(
            reverse("login"),
            data={"login": "1234567", "senha": "x"},
            format="json",
            HTTP_X_API_KEY="chave-errada",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_com_sucesso_autentica_no_keycloak(self) -> None:
        """Deve autenticar contra o Keycloak e retornar identidade+roles."""
        resultado = {
            "autenticado": True,
            "kc_user_id": "5c29cc47-...",
            "username": "1234567",
            "nome": "FULANO DE TAL",
            "email": "fulano@sme.sp.gov.br",
            "ativo": True,
            "cpf": "12345678900",
            "rf": "1234567",
            "roles": {
                "realm_access": {"roles": ["default-roles-cotic"]},
                "resource_access": {"auto-servico-qa": {"roles": ["COTIC"]}},
            },
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.autenticar.return_value = resultado
            response = APIClient().post(
                reverse("login"),
                data={"login": "1234567", "senha": "x"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert corpo["kc_user_id"] == "5c29cc47-..."
        assert corpo["username"] == "1234567"
        assert corpo["access_token"] == "token-jwt"
        assert corpo["roles"]["realm_access"] == {
            "roles": ["default-roles-cotic"]
        }
        assert corpo["roles"]["resource_access"]["auto-servico-qa"] == {
            "roles": ["COTIC"]
        }
        mock_keycloak_admin.autenticar.assert_called_once_with("1234567", "x")

    def test_login_com_senha_invalida_retorna_401(self) -> None:
        """Deve retornar 401 quando a autenticação falhar por senha."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.autenticar.return_value = {
                "autenticado": False,
                "erro": "invalid_grant",
            }
            response = APIClient().post(
                reverse("login"),
                data={"login": "1234567", "senha": "errada"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_usuario_nao_encontrado_retorna_404(self) -> None:
        """Deve retornar 404 quando o login não existir no Keycloak."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.autenticar.return_value = {
                "autenticado": False,
                "erro": "usuário não encontrado",
            }
            response = APIClient().post(
                reverse("login"),
                data={"login": "0000000", "senha": "x"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dados_usuario_retorna_dados_reais(self) -> None:
        """Deve retornar os dados cadastrais consultados no Keycloak."""
        dados = {
            "kc_user_id": "5c29cc47-...",
            "username": "1234567",
            "nome": "FULANO DE TAL",
            "email": "fulano@sme.sp.gov.br",
            "ativo": True,
            "cpf": "12345678900",
            "rf": "1234567",
        }
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.obter_dados_usuario.return_value = dados
            response = APIClient().get(
                reverse("usuario-dados", kwargs={"login": "1234567"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["rf"] == "1234567"
        mock_keycloak_admin.obter_dados_usuario.assert_called_once_with(
            "1234567"
        )

    def test_dados_usuario_nao_encontrado_retorna_404(self) -> None:
        """Deve retornar 404 quando o usuário não existir no Keycloak."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.obter_dados_usuario.return_value = None
            response = APIClient().get(
                reverse("usuario-dados", kwargs={"login": "0000000"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_perfis_por_login_retorna_mock(self) -> None:
        """Deve retornar perfis mockados vinculados ao login."""
        response = APIClient().get(
            reverse("usuario-perfis", kwargs={"login": "1234567"}),
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert len(corpo["perfis"]) >= 1

    def test_dados_acesso_retorna_mock(self) -> None:
        """Deve retornar token enriquecido e permissões mockados."""
        response = APIClient().get(
            reverse(
                "usuario-dados-acesso",
                kwargs={"login": "1234567", "perfil": "professor"},
            ),
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert "token" in corpo
        assert "permissoes" in corpo
