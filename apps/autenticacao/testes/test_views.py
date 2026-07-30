"""Testes das views do fluxo de login e níveis de acesso."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
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


_PERMISSOES = [
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
    "permissoes": _PERMISSOES,
}


def _mock_cliente(
    resposta: httpx.Response,
) -> MagicMock:
    """Mock do cliente HTTP do Token-MS."""
    cliente = MagicMock()

    cliente.__enter__.return_value = cliente

    cliente.get.return_value = resposta
    cliente.post.return_value = resposta

    return cliente


def _resposta_perfis_token_ms(
    corpo: dict,
    status_code: int = 200,
) -> httpx.Response:
    """Resposta simulada do endpoint de perfis."""
    return httpx.Response(
        status_code,
        json=corpo,
        request=httpx.Request(
            "GET",
            (
                "http://token-ms/api/v1/perfis/"
                f"{_CONTA_KEYCLOAK['kc_user_id']}/"
            ),
        ),
    )


def _resposta_token_enriquecido(
    corpo: dict,
    status_code: int = 200,
) -> httpx.Response:
    """Resposta simulada da geração do token enriquecido."""
    return httpx.Response(
        status_code,
        json=corpo,
        request=httpx.Request(
            "POST",
            (
                "http://token-ms/api/v1/token/enriquecido/"
                f"{_CONTA_KEYCLOAK['kc_user_id']}/"
            ),
        ),
    )


class TestAutenticacaoEndpoints:
    """Testes dos endpoints de autenticação."""

    @pytest.fixture(autouse=True)
    def _configura_api_key(
        self,
        settings: Any,
    ) -> None:
        """Configura autenticação dos testes."""
        settings.API_KEY = "chave-secreta"
        settings.API_KEY_HEADER = "X-API-Key"

        settings.JWT_ENRIQUECIDO_ALGORITMO = "RS256"

    def test_login_sem_api_key_retorna_401(self) -> None:
        """Deve bloquear sem API Key."""
        response = APIClient().post(
            reverse("login"),
            data={
                "login": "1234567",
                "senha": "x",
            },
            format="json",
        )

        assert response.status_code == (status.HTTP_401_UNAUTHORIZED)

    def test_login_com_api_key_invalida_retorna_401(
        self,
    ) -> None:
        """Deve bloquear API Key inválida."""
        response = APIClient().post(
            reverse("login"),
            data={
                "login": "1234567",
                "senha": "x",
            },
            format="json",
            HTTP_X_API_KEY="errada",
        )

        assert response.status_code == (status.HTTP_401_UNAUTHORIZED)

    def test_login_com_sucesso_retorna_token_enriquecido(
        self,
    ) -> None:
        """Deve autenticar e retornar token enriquecido."""
        resultado = {
            "autenticado": True,
            **_CONTA_KEYCLOAK,
            "roles": {"realm_access": {"roles": ["default-roles-cotic"]}},
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }

        resposta_token = _resposta_token_enriquecido(
            {
                "token": "jwt-enriquecido",
                "data_expiracao": ("2026-07-24T20:00:00Z"),
            }
        )

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta_token),
            ) as mock_cliente_token_ms,
        ):
            mock_keycloak_admin.autenticar.return_value = resultado

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "1234567",
                    "senha": "x",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 200

        corpo = response.json()

        assert corpo["kc_user_id"] == (_CONTA_KEYCLOAK["kc_user_id"])

        assert corpo["access_token"] == "token-jwt"

        assert corpo["token_enriquecido"] == ("jwt-enriquecido")

        assert corpo["data_expiracao_token_enriquecido"] is not None

        mock_keycloak_admin.autenticar.assert_called_once_with(
            "1234567",
            "x",
        )

        cliente = mock_cliente_token_ms.return_value.__enter__.return_value

        cliente.post.assert_called_once()

    def test_login_com_token_ms_indisponivel_nao_falha(
        self,
    ) -> None:
        """Login deve continuar mesmo sem Token-MS."""
        resultado = {
            "autenticado": True,
            **_CONTA_KEYCLOAK,
            "roles": {},
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }

        cliente = MagicMock()

        cliente.__enter__.return_value = cliente

        cliente.post.side_effect = httpx.ConnectError("recusado")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=cliente,
            ),
        ):
            mock_keycloak_admin.autenticar.return_value = resultado

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "1234567",
                    "senha": "x",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 200

        corpo = response.json()

        assert corpo["token_enriquecido"] is None

        assert corpo["data_expiracao_token_enriquecido"] is None

    def test_login_com_token_ms_erro_nao_falha(
        self,
    ) -> None:
        """Login deve continuar quando Token-MS retorna erro."""
        resultado = {
            "autenticado": True,
            **_CONTA_KEYCLOAK,
            "roles": {},
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }

        resposta = _resposta_token_enriquecido(
            {"erro": "falha interna"},
            status_code=500,
        )

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta),
            ),
        ):
            mock_keycloak_admin.autenticar.return_value = resultado

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "1234567",
                    "senha": "x",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 200

        corpo = response.json()

        assert corpo["token_enriquecido"] is None

    def test_login_com_senha_invalida_retorna_401(
        self,
    ) -> None:
        """Deve retornar 401 para senha inválida."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.autenticar.return_value = {
                "autenticado": False,
                "erro": "invalid_grant",
            }

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "1234567",
                    "senha": "errada",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 401

    def test_login_usuario_nao_encontrado_retorna_204(
        self,
    ) -> None:
        """Usuário inexistente retorna 204."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.autenticar.return_value = {
                "autenticado": False,
                "erro": "usuário não encontrado",
            }

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "0000000",
                    "senha": "x",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 204
        assert not response.content

    def test_dados_usuario_retorna_dados_reais(
        self,
    ) -> None:
        """Deve retornar dados do Keycloak."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-dados",
                    kwargs={"login": "1234567"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 200

        assert response.json()["rf"] == ("1234567")

    def test_dados_usuario_nao_encontrado_retorna_204(
        self,
    ) -> None:
        """Usuário inexistente retorna 204."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.obter_dados_usuario.return_value = None

            response = APIClient().get(
                reverse(
                    "usuario-dados",
                    kwargs={"login": "0000000"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 204
        assert not response.content

    def test_perfis_por_login_retorna_projecao_real_do_token_ms(
        self,
    ) -> None:
        """Deve retornar perfis vindos do Token-MS."""
        resposta_token_ms = _resposta_perfis_token_ms(_PROJECAO_TOKEN_MS)

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
                reverse(
                    "usuario-perfis",
                    kwargs={"login": "1234567"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 200

        corpo = response.json()

        assert corpo["rf"] == "1234567"

        assert corpo["perfis"][0]["nome"] == ("professor")

        cliente = mock_cliente_token_ms.return_value.__enter__.return_value

        cliente.get.assert_called_once_with(
            "/api/v1/perfis/" f"{_CONTA_KEYCLOAK['kc_user_id']}/"
        )

    def test_perfis_por_login_sem_conta_keycloak_retorna_204(
        self,
    ) -> None:
        """Não deve chamar Token-MS sem usuário."""
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_CLIENTE_TOKEN_MS) as mock_cliente_token_ms,
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = None

            response = APIClient().get(
                reverse(
                    "usuario-perfis",
                    kwargs={"login": "0000000"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 204

        mock_cliente_token_ms.assert_not_called()

    def test_perfis_por_login_sem_projecao_retorna_204(
        self,
    ) -> None:
        """Deve retornar 204 quando não existir projeção."""
        resposta = _resposta_perfis_token_ms(
            {"detail": ("Projeção de usuário não encontrada.")},
            status_code=404,
        )

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta),
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-perfis",
                    kwargs={"login": "1234567"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 204

    def test_perfis_por_login_com_timeout_retorna_504(
        self,
    ) -> None:
        """Timeout do Token-MS retorna 504."""
        cliente = MagicMock()

        cliente.__enter__.return_value = cliente

        cliente.get.side_effect = httpx.TimeoutException("timeout")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=cliente,
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-perfis",
                    kwargs={"login": "1234567"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 504

    def test_perfis_por_login_token_ms_indisponivel_retorna_502(
        self,
    ) -> None:
        """Erro de transporte retorna 502."""
        cliente = MagicMock()

        cliente.__enter__.return_value = cliente

        cliente.get.side_effect = httpx.TransportError("falha conexão")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=cliente,
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-perfis",
                    kwargs={"login": "1234567"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 502

    def test_dados_acesso_retorna_token_e_permissoes(
        self,
    ) -> None:
        """Deve retornar token enriquecido e permissões."""
        resposta = _resposta_token_enriquecido(
            {
                "token": "jwt-enriquecido",
                "data_expiracao": ("2026-07-24T20:00:00Z"),
                "permissoes": _PERMISSOES,
            }
        )

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta),
            ) as mock_cliente_token_ms,
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={
                        "login": "1234567",
                        "perfil": "professor",
                    },
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 200

        corpo = response.json()

        assert corpo["token"] == ("jwt-enriquecido")

        assert corpo["permissoes"][0]["sistema_nome"] == "CoreSSO"

        cliente = mock_cliente_token_ms.return_value.__enter__.return_value

        cliente.post.assert_called_once_with(
            ("/api/v1/token/enriquecido/" f"{_CONTA_KEYCLOAK['kc_user_id']}/"),
            json={
                **_CONTA_KEYCLOAK,
                "perfil": "professor",
            },
        )

    def test_dados_acesso_sem_conta_keycloak_retorna_204(
        self,
    ) -> None:
        """Não deve chamar Token-MS sem usuário."""
        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_CLIENTE_TOKEN_MS) as mock_cliente_token_ms,
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = None

            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={
                        "login": "0000000",
                        "perfil": "professor",
                    },
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 204

        mock_cliente_token_ms.assert_not_called()

    def test_dados_acesso_sem_projecao_retorna_204(
        self,
    ) -> None:
        """Token-MS sem usuário retorna 204."""
        resposta = _resposta_token_enriquecido(
            {"detail": ("Projeção não encontrada")},
            status_code=404,
        )

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta),
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={
                        "login": "1234567",
                        "perfil": "professor",
                    },
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 204

    def test_dados_acesso_com_timeout_retorna_504(
        self,
    ) -> None:
        """Timeout ao gerar token retorna 504."""
        cliente = MagicMock()

        cliente.__enter__.return_value = cliente

        cliente.post.side_effect = httpx.TimeoutException("timeout")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=cliente,
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={
                        "login": "1234567",
                        "perfil": "professor",
                    },
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 504

    def test_dados_acesso_token_ms_indisponivel_retorna_502(
        self,
    ) -> None:
        """Falha de conexão retorna 502."""
        cliente = MagicMock()

        cliente.__enter__.return_value = cliente

        cliente.post.side_effect = httpx.TransportError("falha conexão")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=cliente,
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={
                        "login": "1234567",
                        "perfil": "professor",
                    },
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 502

    def test_perfis_por_login_com_erro_generico_token_ms_retorna_erro(
        self,
    ) -> None:
        """Deve repassar erro do Token-MS."""
        resposta = _resposta_perfis_token_ms(
            {"erro": "erro interno"},
            status_code=500,
        )

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta),
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-perfis",
                    kwargs={"login": "1234567"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 500

    def test_dados_acesso_com_erro_generico_token_ms_retorna_erro(
        self,
    ) -> None:
        """Deve repassar erro do Token-MS."""
        resposta = _resposta_token_enriquecido(
            {"erro": "erro interno"},
            status_code=500,
        )

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(
                _CLIENTE_TOKEN_MS,
                return_value=_mock_cliente(resposta),
            ),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = (
                _CONTA_KEYCLOAK
            )

            response = APIClient().get(
                reverse(
                    "usuario-dados-acesso",
                    kwargs={
                        "login": "1234567",
                        "perfil": "professor",
                    },
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == 500
