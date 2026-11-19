"""Contrato HTTP do SGP preservado na borda do Gateway."""

import json
from unittest.mock import patch

import httpx
import pytest
from django.test import override_settings
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

BASE = "/identidade-gateway/api/v1/eol-autenticacao/"


@pytest.mark.parametrize(
    "media", ["application/json", "application/json-patch+json"]
)
@override_settings(API_KEY="teste")
def test_solicitar_aceita_cliente_sgp(media: str) -> None:
    """Usa a chave padrão e repassa login e sistema sem dados locais."""
    with patch(
        "apps.eol_autenticacao.recuperacao_senha.get_api_client"
    ) as obter:
        obter.return_value.post.return_value = httpx.Response(
            200, json="usuario@example.com"
        )
        resposta = APIClient().post(
            f"{BASE}RecuperarSenha/usuario?sistema=1",
            data=json.dumps("1234567"),
            content_type=media,
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 200
    assert resposta.json() == "usuario@example.com"
    chamada = obter.return_value.post.call_args
    assert chamada.kwargs["payload"] == "1234567"
    assert chamada.kwargs["params"] == {"sistema": 1}


@pytest.mark.parametrize("final", ["", "/"])
@override_settings(API_KEY="teste")
def test_alterar_com_formulario_e_barra_final(final: str) -> None:
    """Repassa o formulário usado pelo backend do SGP e devolve o login."""
    with patch(
        "apps.eol_autenticacao.recuperacao_senha.get_api_client"
    ) as obter:
        obter.return_value.post.return_value = httpx.Response(
            200, json="1234567"
        )
        resposta = APIClient().post(
            f"{BASE}AlterarSenha{final}",
            data="token=00000000-0000-0000-0000-000000000001&senha=NovaSenha123",
            content_type="application/x-www-form-urlencoded",
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 200
    assert resposta.json() == "1234567"
    assert (
        obter.return_value.post.call_args.kwargs["payload"]["Senha"]
        == "NovaSenha123"
    )


@override_settings(API_KEY="teste")
def test_validar_preserva_booleano_e_media_type_sgp() -> None:
    """A consulta devolve falso como JSON booleano, sem envelope."""
    with patch(
        "apps.eol_autenticacao.recuperacao_senha.get_api_client"
    ) as obter:
        obter.return_value.post.return_value = httpx.Response(200, json=False)
        resposta = APIClient().post(
            f"{BASE}RecuperarSenha/token/validar",
            data=json.dumps("00000000-0000-0000-0000-000000000001"),
            content_type="application/json-patch+json",
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 200
    assert resposta.json() is False


@override_settings(API_KEY="teste")
def test_preserva_erro_negocio() -> None:
    """Mantém o status e a mensagem do serviço responsável pela recuperação."""
    with patch(
        "apps.eol_autenticacao.recuperacao_senha.get_api_client"
    ) as obter:
        obter.return_value.post.return_value = httpx.Response(
            401, json="Token inválido ou expirado."
        )
        resposta = APIClient().post(
            f"{BASE}AlterarSenha",
            {"Token": "codigo", "Senha": "NovaSenha123"},
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 401
    assert resposta.json() == "Token inválido ou expirado."


@pytest.mark.parametrize(
    "operacao",
    ["RecuperarSenha/usuario", "RecuperarSenha/token/validar", "AlterarSenha"],
)
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"HTTP_X_API_KEY": "invalida"},
        {"HTTP_X_API_EOL_KEY": "teste"},
    ],
)
@override_settings(API_KEY="teste", API_KEY_HEADER="X-API-Key")
def test_exige_api_key_padrao_sem_chamar_ms_token(
    operacao: str, headers: dict[str, str]
) -> None:
    """Rejeita chave ausente, inválida ou enviada só no header legado."""
    with patch(
        "apps.eol_autenticacao.recuperacao_senha.get_api_client"
    ) as obter:
        resposta = APIClient().post(
            f"{BASE}{operacao}",
            {"Token": "codigo", "Senha": "NovaSenha123"},
            **headers,
        )
    assert resposta.status_code == 401
    obter.assert_not_called()


@override_settings(API_KEY="teste", API_KEY_HEADER="X-Identidade-Key")
def test_respeita_cabecalho_configurado() -> None:
    """Usa API_KEY_HEADER como no endpoint de validação de e-mail."""
    with patch(
        "apps.eol_autenticacao.recuperacao_senha.get_api_client"
    ) as obter:
        obter.return_value.post.return_value = httpx.Response(
            200, json="usuario@example.com"
        )
        resposta = APIClient().post(
            f"{BASE}RecuperarSenha/usuario?sistema=1",
            data=json.dumps("1234567"),
            content_type="application/json",
            HTTP_X_IDENTIDADE_KEY="teste",
        )
    assert resposta.status_code == 200
    assert resposta.json() == "usuario@example.com"


@override_settings(API_KEY_HEADER="X-Identidade-Key")
def test_schema_usa_mesma_api_key_da_validacao_de_email() -> None:
    """As três rotas compartilham o esquema padrão de autenticação."""
    schema = SchemaGenerator().get_schema(request=None, public=True)
    operacao_sgp = schema["paths"][
        "/identidade-gateway/api/v1/eol-autenticacao-sgp/"
        "{login}/ValidarEmailExistente/{email}"
    ]["get"]
    for operacao in (
        "RecuperarSenha/usuario",
        "RecuperarSenha/token/validar",
        "AlterarSenha/",
    ):
        assert schema["paths"][f"{BASE}{operacao}"]["post"][
            "security"
        ] == operacao_sgp["security"] == [{"ApiKeyAuth": []}]
    esquemas = schema["components"]["securitySchemes"]
    assert esquemas["ApiKeyAuth"]["name"] == "X-Identidade-Key"
    assert "ApiKeyLegado" not in esquemas
    assert not any(
        caminho.startswith("/api/v1/autenticacao/")
        for caminho in schema["paths"]
    )
