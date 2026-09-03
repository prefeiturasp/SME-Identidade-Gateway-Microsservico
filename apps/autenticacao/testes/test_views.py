"""Testes das views do fluxo de login e níveis de acesso."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

_KEYCLOAK_ADMIN = "apps.autenticacao.api.views.keycloak_admin"
_TOKEN_MS_CLIENT = "apps.autenticacao.api.views._client"


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

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

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

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_com_sucesso_retorna_token_enriquecido(
        self,
    ) -> None:
        """Deve autenticar e retornar token enriquecido."""
        resultado = {
            "autenticado": True,
            **_CONTA_KEYCLOAK,
            "roles": {
                "realm_access": {
                    "roles": ["default-roles-cotic"],
                }
            },
            "access_token": "token-jwt",
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }

        resposta_token = _resposta_token_enriquecido(
            {
                "token": "jwt-enriquecido",
                "data_expiracao": "2026-07-24T20:00:00Z",
            }
        )

        cliente = _mock_cliente(resposta_token)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
        ):
            mock_keycloak_admin.autenticar.return_value = resultado.copy()

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "1234567",
                    "senha": "x",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK

        corpo = response.json()

        assert corpo["kc_user_id"] == _CONTA_KEYCLOAK["kc_user_id"]
        assert corpo["access_token"] == "token-jwt"
        assert corpo["token_enriquecido"] == "jwt-enriquecido"
        assert corpo["data_expiracao_token_enriquecido"] is not None

        mock_keycloak_admin.autenticar.assert_called_once_with(
            "1234567",
            "x",
        )

        cliente.post.assert_called_once_with(
            ("/api/v1/token/enriquecido/" f"{_CONTA_KEYCLOAK['kc_user_id']}/"),
            payload={
                **resultado,
                "perfil": None,
            },
        )

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
        cliente.post.side_effect = httpx.ConnectError("recusado")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
        ):
            mock_keycloak_admin.autenticar.return_value = resultado.copy()

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "1234567",
                    "senha": "x",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK

        corpo = response.json()

        assert corpo["token_enriquecido"] is None
        assert corpo["data_expiracao_token_enriquecido"] is None

        cliente.post.assert_called_once()

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

        cliente = _mock_cliente(resposta)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
        ):
            mock_keycloak_admin.autenticar.return_value = resultado.copy()

            response = APIClient().post(
                reverse("login"),
                data={
                    "login": "1234567",
                    "senha": "x",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK

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

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

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

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

    def test_logout_sem_api_key_retorna_401(self) -> None:
        """Deve bloquear sem API Key."""
        response = APIClient().post(
            reverse("logout"),
            data={"refresh_token": "token-qualquer"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_sem_refresh_token_retorna_400(self) -> None:
        """Deve recusar o corpo sem refresh_token."""
        response = APIClient().post(
            reverse("logout"),
            data={},
            format="json",
            HTTP_X_API_KEY="chave-secreta",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_encerra_sessao_e_dispara_gatilho(self) -> None:
        """Deve encerrar a sessão e disparar o gatilho de auditoria."""
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.encerrar_sessao.return_value = {
                "encerrada": True,
                "kc_user_id": _CONTA_KEYCLOAK["kc_user_id"],
            }

            response = APIClient().post(
                reverse("logout"),
                data={"refresh_token": "refresh-valido"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "situacao": "sessao_encerrada",
        }

        mock_keycloak_admin.encerrar_sessao.assert_called_once_with(
            "refresh-valido"
        )

    def test_logout_com_token_ja_invalido_nao_falha(
        self,
    ) -> None:
        """Deve responder normalmente mesmo com token já expirado.

        O resultado prático (sessão encerrada) já é o mesmo, então a
        resposta ao cliente não deve distinguir os dois casos.
        """
        with patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin:
            mock_keycloak_admin.encerrar_sessao.return_value = {
                "encerrada": False,
                "kc_user_id": None,
            }

            response = APIClient().post(
                reverse("logout"),
                data={"refresh_token": "refresh-expirado"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK

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

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["rf"] == "1234567"

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

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

    def test_perfis_por_login_retorna_projecao_real_do_token_ms(
        self,
    ) -> None:
        """Deve retornar perfis vindos do Token-MS."""
        resposta_token_ms = _resposta_perfis_token_ms(_PROJECAO_TOKEN_MS)

        cliente = _mock_cliente(resposta_token_ms)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_200_OK

        corpo = response.json()

        assert corpo["rf"] == "1234567"
        assert corpo["perfis"][0]["nome"] == "professor"

        cliente.get.assert_called_once_with(
            f"/api/v1/perfis/{_CONTA_KEYCLOAK['kc_user_id']}/"
        )

    def test_perfis_por_login_sem_conta_keycloak_retorna_204(
        self,
    ) -> None:
        """Não deve chamar Token-MS sem usuário."""
        cliente = MagicMock()

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
        ):
            mock_keycloak_admin.obter_dados_usuario.return_value = None

            response = APIClient().get(
                reverse(
                    "usuario-perfis",
                    kwargs={"login": "0000000"},
                ),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        cliente.get.assert_not_called()

    def test_perfis_por_login_sem_projecao_retorna_204(
        self,
    ) -> None:
        """Deve retornar 204 quando não existir projeção."""
        resposta = _resposta_perfis_token_ms(
            {
                "detail": "Projeção de usuário não encontrada.",
            },
            status_code=404,
        )

        cliente = _mock_cliente(resposta)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_perfis_por_login_com_timeout_retorna_504(
        self,
    ) -> None:
        """Timeout do Token-MS retorna 504."""
        cliente = MagicMock()
        cliente.get.side_effect = httpx.TimeoutException("timeout")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    def test_perfis_por_login_token_ms_indisponivel_retorna_502(
        self,
    ) -> None:
        """Erro de transporte retorna 502."""
        cliente = MagicMock()
        cliente.get.side_effect = httpx.TransportError("falha conexão")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_dados_acesso_retorna_token_e_permissoes(
        self,
    ) -> None:
        """Deve retornar token enriquecido e permissões."""
        resposta = _resposta_token_enriquecido(
            {
                "token": "jwt-enriquecido",
                "data_expiracao": "2026-07-24T20:00:00Z",
                "permissoes": _PERMISSOES,
            }
        )

        cliente = _mock_cliente(resposta)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_200_OK

        corpo = response.json()

        assert corpo["token"] == "jwt-enriquecido"
        assert corpo["permissoes"][0]["sistema_nome"] == "CoreSSO"

        cliente.post.assert_called_once_with(
            ("/api/v1/token/enriquecido/" f"{_CONTA_KEYCLOAK['kc_user_id']}/"),
            payload={
                **_CONTA_KEYCLOAK,
                "perfil": "professor",
            },
        )

    def test_dados_acesso_sem_conta_keycloak_retorna_204(
        self,
    ) -> None:
        """Não deve chamar Token-MS sem usuário."""
        cliente = MagicMock()

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_204_NO_CONTENT

        cliente.post.assert_not_called()

    def test_dados_acesso_sem_projecao_retorna_204(
        self,
    ) -> None:
        """Token-MS sem usuário retorna 204."""
        resposta = _resposta_token_enriquecido(
            {
                "detail": "Projeção não encontrada",
            },
            status_code=404,
        )

        cliente = _mock_cliente(resposta)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_dados_acesso_com_timeout_retorna_504(
        self,
    ) -> None:
        """Timeout ao gerar token retorna 504."""
        cliente = MagicMock()
        cliente.post.side_effect = httpx.TimeoutException("timeout")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    def test_dados_acesso_token_ms_indisponivel_retorna_502(
        self,
    ) -> None:
        """Falha de conexão retorna 502."""
        cliente = MagicMock()
        cliente.post.side_effect = httpx.TransportError("falha conexão")

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_perfis_por_login_com_erro_generico_token_ms_retorna_erro(
        self,
    ) -> None:
        """Deve repassar erro do Token-MS."""
        resposta = _resposta_perfis_token_ms(
            {
                "erro": "erro interno",
            },
            status_code=500,
        )

        cliente = _mock_cliente(resposta)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_dados_acesso_com_erro_generico_token_ms_retorna_erro(
        self,
    ) -> None:
        """Deve repassar erro do Token-MS."""
        resposta = _resposta_token_enriquecido(
            {
                "erro": "erro interno",
            },
            status_code=500,
        )

        cliente = _mock_cliente(resposta)

        with (
            patch(_KEYCLOAK_ADMIN) as mock_keycloak_admin,
            patch(_TOKEN_MS_CLIENT, cliente),
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

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def _resposta_validar_token(
    corpo: dict,
    status_code: int = 200,
) -> httpx.Response:
    """Resposta simulada do endpoint de validação de token."""
    return httpx.Response(
        status_code,
        json=corpo,
        request=httpx.Request(
            "POST",
            "http://token-ms/api/v1/token/validar/",
        ),
    )


class TestValidarTokenView:
    """Testes da view ValidarTokenView (proxy para o Token-MS)."""

    @pytest.fixture(autouse=True)
    def _configura_api_key(
        self,
        settings: Any,
    ) -> None:
        """Configura autenticação dos testes."""
        settings.API_KEY = "chave-secreta"
        settings.API_KEY_HEADER = "X-API-Key"

    def test_validar_token_valido_repassa_claims(
        self,
    ) -> None:
        """Deve repassar valido/expirado/claims do Token-MS."""
        claims = {
            "sub": _CONTA_KEYCLOAK["kc_user_id"],
            "rf": _CONTA_KEYCLOAK["rf"],
            "vinculos": [
                {
                    "tipo_vinculo": "cargo_base",
                }
            ],
            "perfis": [],
            "permissoes": [],
        }

        resposta = _resposta_validar_token(
            {
                "valido": True,
                "expirado": False,
                "claims": claims,
            }
        )

        cliente = _mock_cliente(resposta)

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().post(
                reverse("validar-token"),
                {
                    "token": "jwt-enriquecido",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK

        corpo = response.json()

        assert corpo["valido"] is True
        assert corpo["claims"]["vinculos"] == [
            {
                "tipo_vinculo": "cargo_base",
            }
        ]

        cliente.post.assert_called_once_with(
            "/api/v1/token/validar/",
            payload={
                "token": "jwt-enriquecido",
            },
        )

    def test_validar_token_expirado(self) -> None:
        """Token expirado não deve trazer claims."""
        resposta = _resposta_validar_token(
            {
                "valido": False,
                "expirado": True,
            },
            status_code=401,
        )

        cliente = _mock_cliente(resposta)

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().post(
                reverse("validar-token"),
                {
                    "token": "jwt-expirado",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        corpo = response.json()

        assert corpo["valido"] is False
        assert corpo["expirado"] is True
        assert "claims" not in corpo

    def test_validar_token_sem_token_retorna_400(
        self,
    ) -> None:
        """Payload sem `token` não deve chamar o Token-MS."""
        cliente = MagicMock()

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().post(
                reverse("validar-token"),
                {},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        cliente.post.assert_not_called()

    def test_validar_token_com_timeout_retorna_504(
        self,
    ) -> None:
        """Timeout ao validar retorna 504."""
        cliente = MagicMock()
        cliente.post.side_effect = httpx.TimeoutException("timeout")

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().post(
                reverse("validar-token"),
                {
                    "token": "jwt-enriquecido",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    def test_validar_token_ms_indisponivel_retorna_502(
        self,
    ) -> None:
        """Falha de conexão retorna 502."""
        cliente = MagicMock()
        cliente.post.side_effect = httpx.TransportError("falha conexão")

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().post(
                reverse("validar-token"),
                {
                    "token": "jwt-enriquecido",
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_validar_token_sem_api_key_retorna_401(
        self,
    ) -> None:
        """Deve exigir API Key, mesmo padrão das demais rotas."""
        response = APIClient().post(
            reverse("validar-token"),
            {
                "token": "jwt-enriquecido",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
