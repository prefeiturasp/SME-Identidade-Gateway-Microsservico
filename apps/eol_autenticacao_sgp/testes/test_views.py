"""Testes da view so app EOL autenticação SGP."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.eol_autenticacao_sgp.services import (
    ConsultaCoreSSOError,
    IntegracaoETLError,
)

_SERVICO = "apps.eol_autenticacao_sgp.api.views.ServicoDadosUsuario"
_NOME_ROTA = "eol-autenticacao-sgp-dados-usuario"

_DADOS_USUARIO = {
    "cpf": "00123456789",
    "nome": "USUARIO TESTE",
    "codigoRf": "1234567",
    "email": "usuario@exemplo.com",
    "dreCodigo": None,
    "emailValido": True,
}


@pytest.fixture
def cliente(settings: Any) -> APIClient:
    """Fornece um cliente autenticado por API Key."""
    settings.API_KEY = "chave-teste"
    settings.API_KEY_HEADER = "X-API-Key"

    cliente_api = APIClient()
    cliente_api.credentials(HTTP_X_API_KEY="chave-teste")

    return cliente_api


@pytest.fixture
def servico_mocado() -> Generator[MagicMock, None, None]:
    """Substitui o serviço de consulta utilizado pela view."""
    with patch(_SERVICO) as classe_servico:
        yield classe_servico.return_value


def _url(login: str = "1234567") -> str:
    """Resolve a rota de consulta do usuário.

    Args:
        login: Login utilizado na URL.

    Returns:
        Endereço do endpoint do usuário.
    """
    return reverse(
        _NOME_ROTA,
        kwargs={"login": login},
    )


class TestDadosUsuarioView:
    """Testa autenticação e respostas da consulta de usuário."""

    def test_usuario_encontrado_retorna_200_com_dto(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Retorna todos os campos do usuário encontrado."""
        servico_mocado.carregar.return_value = _DADOS_USUARIO

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json() == _DADOS_USUARIO
        servico_mocado.carregar.assert_called_once_with("1234567")

    def test_retorna_dto_parcial_quando_apenas_dre_e_encontrada(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Mantém os campos nulos quando há apenas a DRE."""
        dados = {
            "cpf": None,
            "nome": None,
            "codigoRf": None,
            "email": None,
            "dreCodigo": "108600",
            "emailValido": False,
        }
        servico_mocado.carregar.return_value = dados

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json() == dados

    def test_sem_dados_retorna_204_sem_corpo(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Retorna resposta vazia quando nenhuma fonte encontra dados."""
        servico_mocado.carregar.return_value = None

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_204_NO_CONTENT
        assert resposta.content == b""
        servico_mocado.carregar.assert_called_once_with("1234567")

    @pytest.mark.parametrize(
        ("erro", "mensagem"),
        [
            (
                ConsultaCoreSSOError("Falha SQL"),
                "Houve um problema na conexão com o banco do EOL. "
                "Por favor, contate a SME.",
            ),
            (
                IntegracaoETLError("HTTP 401"),
                "Houve um comportamento inesperado do sistema. "
                "Por favor, contate a SME.",
            ),
            (
                ValueError("Falha inesperada"),
                "Houve um comportamento inesperado do sistema. "
                "Por favor, contate a SME.",
            ),
        ],
    )
    def test_falhas_retorna_400_com_mensagem(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
        erro: Exception,
        mensagem: str,
    ) -> None:
        """Converte falhas do serviço nas mensagens públicas previstas."""
        servico_mocado.carregar.side_effect = erro

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.json() == mensagem

    def test_sem_api_key_retorna_401_sem_consultar_servico(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Impede a consulta quando a API Key não é enviada."""
        cliente.credentials()

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED
        servico_mocado.carregar.assert_not_called()

    def test_api_key_invalida_retorna_401_sem_consultar_servico(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Impede a consulta quando a API Key é inválida."""
        cliente.credentials(HTTP_X_API_KEY="invalida")

        resposta = cliente.get(_url())

        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED
        servico_mocado.carregar.assert_not_called()

    def test_post_retorna_405_sem_consultar_servico(
        self,
        cliente: APIClient,
        servico_mocado: MagicMock,
    ) -> None:
        """Restringe o endpoint ao método GET."""
        resposta = cliente.post(
            _url(),
            {},
            format="json",
        )

        assert resposta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        servico_mocado.carregar.assert_not_called()
