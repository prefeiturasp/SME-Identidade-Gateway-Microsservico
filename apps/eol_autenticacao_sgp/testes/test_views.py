"""Testes da view so app EOL autenticação SGP."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.eol_autenticacao_sgp.services import ConsultaAbrangenciaError

_SERVICO = "apps.eol_autenticacao_sgp.api.views.ServicoDadosUsuario"
_NOME_ROTA = "eol-autenticacao-sgp-dados-usuario"
_ERRO_GERAL = (
    "Houve um comportamento inesperado do sistema. "
    "Por favor, contate a SME."
)

_DADOS_USUARIO = {
    "cpf": "00123456789",
    "nome": "USUARIO TESTE",
    "codigoRf": "1234567",
    "email": "usuario@exemplo.com",
    "dreCodigo": None,
    "emailValido": True,
}

_DADOS_DRE = {
    "cpf": None,
    "nome": None,
    "codigoRf": None,
    "email": None,
    "dreCodigo": "108600",
    "emailValido": False,
}


@pytest.fixture
def cliente(settings: Any) -> APIClient:
    """Fornece cliente HTTP autenticado com API Key de teste."""
    settings.API_KEY = "chave-teste"
    settings.API_KEY_HEADER = "X-API-Key"

    cliente_api = APIClient()
    cliente_api.credentials(HTTP_X_API_KEY="chave-teste")
    return cliente_api


@pytest.fixture
def servico_mocado() -> Generator[MagicMock, None, None]:
    """Simula o serviço de consulta usado pela view."""
    with patch(_SERVICO) as classe_servico:
        yield classe_servico.return_value


def _url(login: str = "7210418") -> str:
    """Retorna a URL de consulta a partir do nome da rota."""
    return str(reverse(_NOME_ROTA, kwargs={"login": login}))


class TestDadosUsuarioView:
    """Valida respostas HTTP, serialização e autenticação da view."""

    def test_usuario_ativo_retorna_200_com_seis_campos(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Devolve o DTO cadastral do usuário ativo."""
        servico_mocado.carregar.return_value = _DADOS_USUARIO.copy()

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json() == _DADOS_USUARIO
        servico_mocado.carregar.assert_called_once_with("1234567")

    def test_usuario_ativo_sem_email_valido_retorna_200(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Preserva os campos nulos produzidos pelo serviço."""
        servico_mocado.carregar.return_value = {
            **_DADOS_USUARIO,
            "email": None,
            "emailValido": False,
        }

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json()["email"] is None
        assert resposta.json()["emailValido"] is False

    def test_dre_encontrada_retorna_200_com_dto_parcial(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Retorna somente a DRE quando não há usuário elegível."""
        servico_mocado.carregar.return_value = _DADOS_DRE.copy()

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json() == _DADOS_DRE
        servico_mocado.carregar.assert_called_once_with("1234567")

    def test_usuario_e_dre_ausentes_retorna_204_sem_corpo(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Retorna No Content quando nenhuma fonte encontra dados."""
        servico_mocado.carregar.return_value = None

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_204_NO_CONTENT
        assert resposta.content == b""
        servico_mocado.carregar.assert_called_once_with("1234567")

    @pytest.mark.parametrize(
        "erro",
        [
            ConsultaAbrangenciaError("MS-Abrangência indisponível"),
            RuntimeError("Keycloak indisponível"),
            ValueError("Resposta inesperada"),
        ],
    )
    def test_falha_tecnica_retorna_400_com_mensagem_legada(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
        erro: Exception,
    ) -> None:
        """Converte falhas das integrações na mensagem pública prevista."""
        servico_mocado.carregar.side_effect = erro

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.json() == _ERRO_GERAL
        servico_mocado.carregar.assert_called_once_with("1234567")

    def test_sem_api_key_retorna_401_sem_consultar_servico(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Bloqueia requisições sem a API Key do Gateway."""
        cliente.credentials()

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED
        servico_mocado.carregar.assert_not_called()

    def test_api_key_invalida_retorna_401_sem_consultar_servico(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Bloqueia requisições com API Key inválida."""
        cliente.credentials(HTTP_X_API_KEY="chave-invalida")

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED
        servico_mocado.carregar.assert_not_called()

    def test_post_retorna_405_sem_consultar_servico(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Não permite método diferente de GET."""
        resposta = cliente.post(_url(), {}, format="json")

        assert resposta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        servico_mocado.carregar.assert_not_called()
