"""Testes HTTP da consulta de e-mail no Keycloak compatível com o SGP."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from keycloak.exceptions import KeycloakError
from rest_framework import status
from rest_framework.test import APIClient

from apps.eol_autenticacao_sgp.services import ConsultaAbrangenciaError

_EMAIL = "Email+SGP@Example.com"
_OBTER_ADMIN = "apps.autenticacao.keycloak_admin.obter_admin_keycloak"

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

def _url_validar_email_existente_sgp(
        login: str = "1234567",
        email: str = _EMAIL
    ) -> str:
    """Monta a URL pelos parâmetros do contrato SGP."""
    url: str = reverse(
        "validar-email-existente", kwargs={"login": login, "email": email}
    )
    return url

@pytest.fixture
def cliente(settings: Any) -> APIClient:
    """Configura um cliente com a API Key habitual do gateway."""
    settings.API_KEY = "chave-teste"
    settings.API_KEY_HEADER = "X-API-Key"
    api = APIClient()
    api.credentials(HTTP_X_API_KEY="chave-teste")
    return api


@pytest.mark.parametrize(
    ("ids", "esperado"),
    [
        ([], False),
        (["conta-atual"], False),
        (["outra-conta"], True),
        (["conta-atual", "outra-conta"], True),
    ],
)
@patch(_OBTER_ADMIN)
def test_retorna_booleano_no_path_atual_sem_redirecionar(
    obter_admin: MagicMock,
    cliente: APIClient,
    ids: list[str],
    esperado: bool,
) -> None:
    """Preserva a rota e exclui a conta por ID mesmo com login RF."""
    admin = obter_admin.return_value
    admin.get_users.side_effect = [
        [],
        [{"id": "conta-atual", "username": "username-diferente-do-rf"}],
        [
            {"id": conta_id, "enabled": False, "emailVerified": False}
            for conta_id in ids
        ],
    ]
    assert _url_validar_email_existente_sgp() == (
        "/identidade-gateway/api/v1/eol-autenticacao-sgp/"
        "1234567/ValidarEmailExistente/" + _EMAIL
    )

    resposta = cliente.get(_url_validar_email_existente_sgp())

    assert resposta.status_code == 200
    assert resposta.json() is esperado
    assert "Location" not in resposta


@pytest.mark.parametrize(
    ("login", "email", "campo"),
    [("   ", _EMAIL, "login"), ("1234567", "invalido", "email")],
)
@patch(_OBTER_ADMIN)
def test_entrada_invalida_nao_consulta_keycloak(
    obter_admin: MagicMock,
    cliente: APIClient,
    login: str,
    email: str,
    campo: str,
) -> None:
    """Rejeita parâmetros inválidos antes de consultar o provedor."""
    resposta = cliente.get(_url_validar_email_existente_sgp(login, email))

    assert resposta.status_code == 400
    assert campo in resposta.json()
    obter_admin.assert_not_called()


@patch(_OBTER_ADMIN)
def test_remove_somente_espacos_externos_dos_parametros(
    obter_admin: MagicMock, cliente: APIClient
) -> None:
    """Mantém a caixa e o sufixo do e-mail ao fazer a consulta exata."""
    admin = obter_admin.return_value
    admin.get_users.side_effect = [[{"id": "conta-atual"}], []]

    resposta = cliente.get(_url_validar_email_existente_sgp(
        " 1234567 ",
        f" {_EMAIL} "
    ))

    assert resposta.status_code == 200
    assert resposta.json() is False
    assert admin.get_users.call_args_list[0].kwargs["query"] == {
        "username": "1234567",
        "exact": True,
    }
    admin.get_users.assert_called_with(query={"email": _EMAIL, "exact": True})


@patch(_OBTER_ADMIN)
def test_login_inexistente_retorna_404(
    obter_admin: MagicMock, cliente: APIClient
) -> None:
    """Não apresenta uma conta inexistente como e-mail disponível."""
    obter_admin.return_value.get_users.return_value = []

    resposta = cliente.get(_url_validar_email_existente_sgp())

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "Usuário não encontrado."}


@pytest.mark.parametrize("etapa", ["cliente", "login", "email"])
@patch(_OBTER_ADMIN)
def test_falha_do_provedor_retorna_502_com_erro_generico(
    obter_admin: MagicMock, cliente: APIClient, etapa: str
) -> None:
    """Falhas não viram false nem expõem detalhes recebidos do SDK."""
    erro = KeycloakError("detalhe interno", response_code=500)
    if etapa == "cliente":
        obter_admin.side_effect = erro
    elif etapa == "login":
        obter_admin.return_value.get_users.side_effect = erro
    else:
        obter_admin.return_value.get_users.side_effect = [
            [{"id": "conta-atual"}],
            erro,
        ]

    resposta = cliente.get(_url_validar_email_existente_sgp())

    assert resposta.status_code == 502
    assert resposta.json() == {"erro": "Provedor de identidade indisponível."}
    assert "detalhe interno" not in resposta.content.decode()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"HTTP_X_API_KEY": "invalida"},
        {"HTTP_X_API_EOL_KEY": "chave-teste"},
    ],
)
@patch(_OBTER_ADMIN)
def test_exige_a_api_key_do_gateway(
    obter_admin: MagicMock, cliente: APIClient, headers: dict[str, str]
) -> None:
    """Rejeita chave ausente, inválida ou enviada só no header legado."""
    cliente.credentials(**headers)

    resposta = cliente.get(_url_validar_email_existente_sgp())

    assert resposta.status_code == 401
    obter_admin.assert_not_called()


@patch(_OBTER_ADMIN)
def test_respeita_header_de_api_key_configurado(
    obter_admin: MagicMock, cliente: APIClient, settings: Any
) -> None:
    """A configuração habitual do gateway continua definindo o header."""
    settings.API_KEY_HEADER = "X-Identidade-Key"
    cliente.credentials(HTTP_X_IDENTIDADE_KEY="chave-teste")
    obter_admin.return_value.get_users.side_effect = [
        [{"id": "conta-atual"}],
        [],
    ]

    resposta = cliente.get(_url_validar_email_existente_sgp())

    assert resposta.status_code == 200
    assert resposta.json() is False


def test_schema_documenta_booleano_parametros_e_api_key() -> None:
    """O contrato documentado mantém o booleano e a chave do gateway."""
    schema = SchemaGenerator().get_schema(request=None, public=True)
    operacao = schema["paths"][
        "/identidade-gateway/api/v1/eol-autenticacao-sgp/"
        "{login}/ValidarEmailExistente/{email}"
    ]["get"]

    assert operacao["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"type": "boolean"}
    assert operacao["security"] == [{"ApiKeyAuth": []}]
    assert {"404", "502"} <= operacao["responses"].keys()
    assert "504" not in operacao["responses"]
    parametros = {
        parametro["name"]: parametro for parametro in operacao["parameters"]
    }
    assert parametros["email"]["schema"]["format"] == "email"
    assert all(parametro["required"] for parametro in parametros.values())

@pytest.fixture
def servico_mocado() -> Generator[MagicMock, None, None]:
    """Simula o serviço de consulta utilizado pela view."""
    with patch(_SERVICO) as classe_servico:
        yield classe_servico.return_value


def _url(login: str = "1234567") -> str:
    """Retorna a URL de consulta a partir do nome da rota."""
    return str(reverse(_NOME_ROTA, kwargs={"login": login}))


def _verificar_consulta_usuario(
    servico_mocado: MagicMock,
    login: str = "1234567",
) -> None:
    """Confere uma única chamada ao serviço com o login esperado."""
    servico_mocado.carregar.assert_called_once()

    assert servico_mocado.carregar.call_args in (
        call(login),
        call(login=login),
    )


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
        _verificar_consulta_usuario(servico_mocado)

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
        assert resposta.json() == {
            **_DADOS_USUARIO,
            "email": None,
            "emailValido": False,
        }
        _verificar_consulta_usuario(servico_mocado)

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
        _verificar_consulta_usuario(servico_mocado)

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
        _verificar_consulta_usuario(servico_mocado)

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
        _verificar_consulta_usuario(servico_mocado)

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