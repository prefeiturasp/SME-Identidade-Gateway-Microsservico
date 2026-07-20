"""Testes das views do domínio de gestão de usuário."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

_CLIENTE_ETL = "apps.gestao_usuario.api.views.cliente_etl"


def _mock_cliente(resposta: httpx.Response) -> MagicMock:
    """Monta um MagicMock de cliente_etl() usável como context manager."""
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.post.return_value = resposta
    cliente.get.return_value = resposta
    return cliente


class TestGestaoUsuarioEndpoints:
    """Testes de autenticação e comportamento das rotas de gestão."""

    @pytest.fixture(autouse=True)
    def _configura_api_key(self, settings: Any) -> None:
        """Define API_KEY/API_KEY_HEADER para o escopo de cada teste."""
        settings.API_KEY = "chave-secreta"
        settings.API_KEY_HEADER = "X-API-Key"

    # -- Criar usuário -------------------------------------------------

    def test_criar_usuario_sem_api_key_retorna_401(self) -> None:
        """Deve rejeitar requisição sem API Key."""
        response = APIClient().post(
            reverse("usuario-criar"),
            data={"nome": "Teste", "cpf": "12345678900"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_usuario_sem_cpf_e_sem_rf_retorna_400(self) -> None:
        """Deve rejeitar payload sem cpf nem rf, sem chamar o ETL."""
        with patch(_CLIENTE_ETL) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-criar"),
                data={"nome": "Teste"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_cliente_etl.assert_not_called()

    def test_criar_usuario_com_sucesso_repassa_ao_etl(self) -> None:
        """Deve repassar o payload validado ao ETL e devolver a resposta."""
        resposta_etl = httpx.Response(
            200,
            json={"acao": "criado", "kc_user_id": "kc-1"},
            request=httpx.Request("POST", "http://etl/usuario/criar/"),
        )
        with patch(
            _CLIENTE_ETL, return_value=_mock_cliente(resposta_etl)
        ) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-criar"),
                data={"nome": "Fulano", "cpf": "12345678900"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["acao"] == "criado"
        cliente = mock_cliente_etl.return_value.__enter__.return_value
        cliente.post.assert_called_once()
        args, kwargs = cliente.post.call_args
        assert args[0] == "/api/v1/etl/usuario/criar/"
        assert kwargs["json"]["nome"] == "Fulano"

    def test_criar_usuario_com_sistema_e_roles_repassa_ao_etl(self) -> None:
        """Deve repassar sistema/roles junto ao payload de criação."""
        resposta_etl = httpx.Response(
            200,
            json={
                "acao": "criado",
                "kc_user_id": "kc-1",
                "roles_atribuidos": ["Admin"],
            },
            request=httpx.Request("POST", "http://etl/usuario/criar/"),
        )
        with patch(
            _CLIENTE_ETL, return_value=_mock_cliente(resposta_etl)
        ) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-criar"),
                data={
                    "nome": "Fulano",
                    "cpf": "12345678900",
                    "sistema": 0,
                    "roles": ["string"],
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["roles_atribuidos"] == ["Admin"]
        cliente = mock_cliente_etl.return_value.__enter__.return_value
        _, kwargs = cliente.post.call_args
        assert kwargs["json"]["sistema"] == 0
        assert kwargs["json"]["roles"] == ["string"]

    def test_criar_usuario_com_roles_sem_sistema_retorna_400(self) -> None:
        """Deve rejeitar roles sem sistema, sem chamar o ETL."""
        with patch(_CLIENTE_ETL) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-criar"),
                data={
                    "nome": "Fulano",
                    "cpf": "12345678900",
                    "roles": ["string"],
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_cliente_etl.assert_not_called()

    def test_criar_usuario_com_sistema_sem_roles_retorna_400(self) -> None:
        """Deve rejeitar sistema sem roles, sem chamar o ETL."""
        with patch(_CLIENTE_ETL) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-criar"),
                data={
                    "nome": "Fulano",
                    "cpf": "12345678900",
                    "sistema": 0,
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_cliente_etl.assert_not_called()

    def test_criar_usuario_com_etl_indisponivel_retorna_502(self) -> None:
        """Deve retornar 502 quando o ETL estiver inacessível."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.post.side_effect = httpx.ConnectError("recusado")

        with patch(_CLIENTE_ETL, return_value=cliente):
            response = APIClient().post(
                reverse("usuario-criar"),
                data={"nome": "Fulano", "cpf": "12345678900"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_criar_usuario_com_timeout_retorna_504(self) -> None:
        """Deve retornar 504 quando o ETL não responder a tempo."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.post.side_effect = httpx.TimeoutException("timeout")

        with patch(_CLIENTE_ETL, return_value=cliente):
            response = APIClient().post(
                reverse("usuario-criar"),
                data={"nome": "Fulano", "cpf": "12345678900"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    def test_criar_usuario_repassa_404_do_etl(self) -> None:
        """Deve repassar o status de erro retornado pelo ETL."""
        resposta_etl = httpx.Response(
            404,
            json={"detalhe": "usuário não encontrado"},
            request=httpx.Request("POST", "http://etl/usuario/criar/"),
        )
        with patch(_CLIENTE_ETL, return_value=_mock_cliente(resposta_etl)):
            response = APIClient().post(
                reverse("usuario-criar"),
                data={"nome": "Fulano", "cpf": "12345678900"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # -- Sincronizar usuário --------------------------------------------

    def test_sincronizar_usuario_sem_identificador_retorna_400(self) -> None:
        """Deve rejeitar payload sem identificador, sem chamar o ETL."""
        with patch(_CLIENTE_ETL) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-sincronizar"),
                data={},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_cliente_etl.assert_not_called()

    def test_sincronizar_usuario_com_sucesso(self) -> None:
        """Deve repassar o identificador ao ETL e devolver a resposta."""
        resposta_etl = httpx.Response(
            200,
            json={"acao": "atualizado", "kc_user_id": "kc-2"},
            request=httpx.Request("POST", "http://etl/usuario/sincronizar/"),
        )
        with patch(_CLIENTE_ETL, return_value=_mock_cliente(resposta_etl)):
            response = APIClient().post(
                reverse("usuario-sincronizar"),
                data={"identificador": "1234567"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["acao"] == "atualizado"

    def test_sincronizar_usuario_com_timeout_retorna_504(self) -> None:
        """Deve retornar 504 quando o ETL não responder a tempo."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.post.side_effect = httpx.TimeoutException("timeout")

        with patch(_CLIENTE_ETL, return_value=cliente):
            response = APIClient().post(
                reverse("usuario-sincronizar"),
                data={"identificador": "1234567"},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    # -- Conceder acesso -------------------------------------------------

    def test_conceder_acesso_sem_roles_retorna_400(self) -> None:
        """Deve rejeitar payload sem roles, sem chamar o ETL."""
        with patch(_CLIENTE_ETL) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-conceder-acesso"),
                data={"identificador": "1234567", "sistema": 1, "roles": []},
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_cliente_etl.assert_not_called()

    def test_conceder_acesso_com_sucesso(self) -> None:
        """Deve repassar identificador, sistema e roles ao ETL."""
        resposta_etl = httpx.Response(
            200,
            json={"acao": "concedido", "roles_atribuidos": ["Admin"]},
            request=httpx.Request(
                "POST", "http://etl/usuario/conceder-acesso/"
            ),
        )
        with patch(
            _CLIENTE_ETL, return_value=_mock_cliente(resposta_etl)
        ) as mock_cliente_etl:
            response = APIClient().post(
                reverse("usuario-conceder-acesso"),
                data={
                    "identificador": "1234567",
                    "sistema": 1,
                    "roles": ["Admin"],
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        cliente = mock_cliente_etl.return_value.__enter__.return_value
        _, kwargs = cliente.post.call_args
        assert kwargs["json"]["roles"] == ["Admin"]

    def test_conceder_acesso_com_timeout_retorna_504(self) -> None:
        """Deve retornar 504 quando o ETL não responder a tempo."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.post.side_effect = httpx.TimeoutException("timeout")

        with patch(_CLIENTE_ETL, return_value=cliente):
            response = APIClient().post(
                reverse("usuario-conceder-acesso"),
                data={
                    "identificador": "1234567",
                    "sistema": 1,
                    "roles": ["Admin"],
                },
                format="json",
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    # -- Consultar identidade ---------------------------------------------

    def test_consultar_identidade_sem_api_key_retorna_401(self) -> None:
        """Deve rejeitar requisição sem API Key."""
        response = APIClient().get(
            reverse("usuario-consultar"), {"cpf": "12345678900"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_consultar_identidade_com_sucesso(self) -> None:
        """Deve repassar os filtros de querystring ao ETL."""
        resposta_etl = httpx.Response(
            200,
            json={"cpf": "12345678900", "situacao": "provisionado"},
            request=httpx.Request("GET", "http://etl/identidades/consultar/"),
        )
        with patch(_CLIENTE_ETL, return_value=_mock_cliente(resposta_etl)):
            response = APIClient().get(
                reverse("usuario-consultar"),
                {"cpf": "12345678900"},
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["situacao"] == "provisionado"

    def test_consultar_identidade_com_etl_indisponivel_retorna_502(
        self,
    ) -> None:
        """Deve retornar 502 quando o ETL estiver inacessível."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.get.side_effect = httpx.ConnectError("recusado")

        with patch(_CLIENTE_ETL, return_value=cliente):
            response = APIClient().get(
                reverse("usuario-consultar"),
                {"cpf": "12345678900"},
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    def test_consultar_identidade_com_resposta_nao_json_retorna_502(
        self,
    ) -> None:
        """Deve retornar 502 se um proxy responder HTML em vez de JSON.

        Reproduz o cenário observado em QA: sem filtros na
        querystring, um proxy/WAF na frente do ETL responde com uma
        página de erro HTML (404 de infraestrutura), não com o JSON
        que o ETL normalmente devolve.
        """
        resposta_etl = httpx.Response(
            404,
            content=b"<html><body>Pagina nao encontrada</body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", "http://etl/identidades/consultar/"),
        )
        with patch(_CLIENTE_ETL, return_value=_mock_cliente(resposta_etl)):
            response = APIClient().get(
                reverse("usuario-consultar"),
                HTTP_X_API_KEY="chave-secreta",
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.json()["status_servico"] == 404
