"""Testes das views do fluxo de login e níveis de acesso."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import jwt
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

_KEYCLOAK_ADMIN = "apps.autenticacao.api.views.keycloak_admin"
_CLIENTE_TOKEN_MS = "apps.autenticacao.api.views.cliente_token_ms"

_CONTA_KEYCLOAK = {
    "kc_user_id": "5c29cc47-...",
    "username": "1234567",
    "nome": "FULANO DE TAL",
    "email": "fulano@sme.sp.gov.br",
    "ativo": True,
    "cpf": "12345678900",
    "rf": "1234567",
}

_PROJECAO_TOKEN_MS = {
    "usuario_id": _CONTA_KEYCLOAK["kc_user_id"],
    "login": "1234567",
    "rf": "1234567",
    "perfis": [
        {
            "id": "b2b2b2b2-0000-0000-0000-000000000000",
            "nome": "professor",
            "ativo": True,
        }
    ],
    "permissoes": [
        {
            "sistema_id": 1,
            "sistema_nome": "CoreSSO",
            "modulo_id": 3,
            "modulo_nome": "Usuários",
            "consultar": True,
            "inserir": False,
            "alterar": False,
            "excluir": False,
        },
    ],
}


def _mock_cliente(resposta: httpx.Response) -> MagicMock:
    """Monta um MagicMock de cliente_token_ms() usável como context manager."""
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.get.return_value = resposta
    return cliente


def _resposta_token_ms(corpo: dict, status_code: int = 200) -> httpx.Response:
    """Monta uma resposta simulada do Token-MS para o usuário de teste."""
    return httpx.Response(
        status_code,
        json=corpo,
        request=httpx.Request(
            "GET",
            f"http://token-ms/api/v1/perfis/{_CONTA_KEYCLOAK['kc_user_id']}/",
        ),
    )


class TestAutenticacaoEndpoints:
    """Testes de autenticação e autorização exigidas pelos endpoints."""

    @pytest.fixture(autouse=True)
    def _configura_api_key(self, settings: Any) -> None:
        """Define API_KEY/API_KEY_HEADER e o secret do token enriquecido."""
        settings.API_KEY = "chave-secreta"
        settings.API_KEY_HEADER = "X-API-Key"
        settings.JWT_ENRIQUECIDO_SECRET = "secret-de-teste"
        settings.JWT_ENRIQUECIDO_ALGORITMO = "HS256"
        settings.JWT_ENRIQUECIDO_TTL_SEGUNDOS = 28800

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

    def test_login_com_sucesso_retorna_resposta_completa(self) -> None:
        """Deve autenticar, compor o token enriquecido e trazer perfis."""
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
        resposta_token_ms = _resposta_token_ms(_PROJECAO_TOKEN_MS)
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta_token_ms),
            ),
        ):
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
        assert "perfis" not in corpo
        assert "permissoes" not in corpo

        claims = jwt.decode(
            corpo["token_enriquecido"],
            "secret-de-teste",
            algorithms=["HS256"],
        )
        assert claims["sub"] == "5c29cc47-..."
        assert claims["rf"] == "1234567"
        assert claims["perfis"][0]["nome"] == "professor"
        assert claims["permissoes"][0]["sistema_nome"] == "CoreSSO"
        assert "perfilSelecionado" not in claims

        mock_keycloak_admin.autenticar.assert_called_once_with("1234567", "x")

    def test_login_com_token_ms_indisponivel_nao_falha(self) -> None:
        """Login não deve falhar se o Token-MS estiver fora do ar."""
        resultado = {
            "autenticado": True,
            "kc_user_id": "5c29cc47-...",
            "username": "1234567",
            "nome": "FULANO DE TAL",
            "email": "fulano@sme.sp.gov.br",
            "ativo": True,
            "cpf": "12345678900",
            "rf": "1234567",
            "roles": {},
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.get.side_effect = httpx.ConnectError("recusado")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_CLIENTE_TOKEN_MS, return_value=cliente),
        ):
            mock_keycloak_admin.autenticar.return_value = resultado
            response = APIClient().post(
                reverse("login"),
                data={"login": "1234567", "senha": "x"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert "token_enriquecido" in corpo
        claims = jwt.decode(
            corpo["token_enriquecido"],
            "secret-de-teste",
            algorithms=["HS256"],
        )
        assert claims["perfis"] == []
        assert claims["permissoes"] == []

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

    def test_login_usuario_nao_encontrado_retorna_204(self) -> None:
        """Deve retornar 204 (não 404) quando o login não existir.

        204 não tem corpo por definição do protocolo HTTP.
        """
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

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

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

    def test_dados_usuario_nao_encontrado_retorna_204(self) -> None:
        """Deve retornar 204 (não 404) quando o usuário não existir."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.obter_dados_usuario.return_value = None
            response = APIClient().get(
                reverse("usuario-dados", kwargs={"login": "0000000"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

    def test_perfis_por_login_retorna_projecao_real_do_token_ms(self) -> None:
        """Deve resolver a conta e consultar o Token-MS de verdade."""
        resposta_token_ms = _resposta_token_ms(_PROJECAO_TOKEN_MS)
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta_token_ms),
            ) as mock_cliente_token_ms,
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )
            response = APIClient().get(
                reverse("usuario-perfis", kwargs={"login": "1234567"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert corpo["rf"] == "1234567"
        assert corpo["perfis"][0]["nome"] == "professor"
        cliente = mock_cliente_token_ms.return_value.__enter__.return_value
        cliente.get.assert_called_once_with(
            f"/api/v1/perfis/{_CONTA_KEYCLOAK['kc_user_id']}/"
        )

    def test_perfis_por_login_sem_conta_no_keycloak_retorna_204(self) -> None:
        """Deve retornar 204 sem chamar o Token-MS se o login não existir."""
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_CLIENTE_TOKEN_MS) as mock_cliente_token_ms,
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = None
            response = APIClient().get(
                reverse("usuario-perfis", kwargs={"login": "0000000"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_cliente_token_ms.assert_not_called()

    def test_perfis_por_login_sem_projecao_no_token_ms_retorna_204(
        self,
    ) -> None:
        """Deve retornar 204 quando o Token-MS não tiver projeção."""
        resposta_token_ms = _resposta_token_ms(
            {"detail": "Projeção de usuário não encontrada."}, 404
        )
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta_token_ms),
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )
            response = APIClient().get(
                reverse("usuario-perfis", kwargs={"login": "1234567"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_perfis_por_login_com_timeout_retorna_504(self) -> None:
        """Deve retornar 504 quando o Token-MS não responder a tempo."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.get.side_effect = httpx.TimeoutException("timeout")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_CLIENTE_TOKEN_MS, return_value=cliente),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )
            response = APIClient().get(
                reverse("usuario-perfis", kwargs={"login": "1234567"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    def test_perfis_por_login_com_token_ms_indisponivel_retorna_502(
        self,
    ) -> None:
        """Deve retornar 502 quando o Token-MS estiver inacessível."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.get.side_effect = httpx.ConnectError("recusado")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_CLIENTE_TOKEN_MS, return_value=cliente),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )
            response = APIClient().get(
                reverse("usuario-perfis", kwargs={"login": "1234567"}),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_dados_acesso_retorna_token_enriquecido_e_permissoes(
        self,
    ) -> None:
        """Deve retornar o token enriquecido e as permissões reais."""
        resposta_token_ms = _resposta_token_ms(_PROJECAO_TOKEN_MS)
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta_token_ms),
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )
            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={"login": "1234567", "perfil": "professor"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert corpo["permissoes"] == [
            {
                "sistema_id": 1,
                "sistema_nome": "CoreSSO",
                "modulo_id": 3,
                "modulo_nome": "Usuários",
                "consultar": True,
                "inserir": False,
                "alterar": False,
                "excluir": False,
            }
        ]

        claims = jwt.decode(
            corpo["token"], "secret-de-teste", algorithms=["HS256"]
        )
        assert claims["sub"] == _CONTA_KEYCLOAK["kc_user_id"]
        assert claims["perfilSelecionado"] == "professor"
        assert claims["permissoes"][0]["sistema_nome"] == "CoreSSO"

    def test_dados_acesso_sem_conta_no_keycloak_retorna_204(self) -> None:
        """Deve retornar 204 sem chamar o Token-MS se o login não existir."""
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_CLIENTE_TOKEN_MS) as mock_cliente_token_ms,
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = None
            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={"login": "0000000", "perfil": "professor"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_cliente_token_ms.assert_not_called()
