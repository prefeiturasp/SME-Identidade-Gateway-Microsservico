"""Contrato HTTP do SGP preservado na borda do Gateway."""

import json
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.test import override_settings
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from apps.eol_autenticacao.services import recuperacao_senha
from apps.provedores.contratos import UsuarioIdentidade
from apps.provedores.excecoes import (
    PoliticaSenhaIncompativelError,
    ProvedorIndisponivelError,
    SenhaNoHistoricoError,
)

BASE = "/identidade-gateway/api/v1/eol-autenticacao/"
TOKEN = "00000000-0000-0000-0000-000000000001"
CONTA = UsuarioIdentidade(
    id="conta-1",
    login="1234567",
    nome="Maria",
    email="usuario@example.com",
    ativo=True,
    rf="1234567",
)


@pytest.fixture(autouse=True)
def provedor() -> Iterator[MagicMock]:
    """Isola o provedor e fornece somente os dados normalizados da conta."""
    with patch.object(recuperacao_senha, "obter_provedor_identidade") as obter:
        obter.return_value.contexto = "identidade-local"
        obter.return_value.buscar_usuario_por_login.return_value = CONTA
        obter.return_value.obter_usuario.return_value = CONTA
        yield obter.return_value


def responder_ms(
    rota: str, *, payload: dict, **kwargs: object
) -> httpx.Response:
    """Simula a reserva e a confirmação usando o identificador do Gateway."""
    if rota.endswith("alteracoes/consultar"):
        return httpx.Response(
            200, json={"usuario_id": CONTA.id, "login": CONTA.login}
        )
    if rota.endswith("alteracoes/reservar"):
        return httpx.Response(
            200,
            json={
                "operacao_id": payload["operacao_id"],
                "usuario_id": CONTA.id,
                "login": CONTA.login,
            },
        )
    if payload["resultado"] == "sucesso":
        return httpx.Response(200, json=CONTA.login)
    status = 401 if payload.get("motivo") == "historico" else 502
    return httpx.Response(status, json="Falha confirmada pelo MS-Token.")


@pytest.mark.parametrize(
    "media", ["application/json", "application/json-patch+json"]
)
@override_settings(API_KEY="teste")
def test_solicitar_aceita_cliente_sgp(media: str) -> None:
    """Usa a chave padrão e repassa login e sistema sem dados locais."""
    with patch(
        "apps.eol_autenticacao.services.recuperacao_senha.get_api_client"
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
    assert chamada.args[0].endswith("/solicitacoes")
    assert chamada.kwargs["payload"]["login"] == "1234567"
    assert chamada.kwargs["payload"]["sistema"] == 1
    assert chamada.kwargs["payload"]["conta"]["id"] == CONTA.id


@pytest.mark.parametrize("final", ["", "/"])
@override_settings(API_KEY="teste")
def test_alterar_com_formulario_e_barra_final(
    final: str, provedor: MagicMock
) -> None:
    """Repassa o formulário usado pelo backend do SGP e devolve o login."""
    with patch(
        "apps.eol_autenticacao.services.recuperacao_senha.get_api_client"
    ) as obter:
        obter.return_value.post.side_effect = responder_ms
        resposta = APIClient().post(
            f"{BASE}AlterarSenha{final}",
            data="token=00000000-0000-0000-0000-000000000001&senha=NovaSenha123",
            content_type="application/x-www-form-urlencoded",
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 200
    assert resposta.json() == "1234567"
    assert (
        obter.return_value.post.call_args_list[1].kwargs["payload"]["senha"]
        == "NovaSenha123"
    )
    provedor.obter_usuario.assert_called_once_with(CONTA.id)
    provedor.preparar_alteracao_senha.assert_called_once_with(
        CONTA.id, historico_minimo=5
    )
    provedor.alterar_senha.assert_called_once_with(CONTA.id, "NovaSenha123")


@override_settings(API_KEY="teste")
def test_validar_preserva_booleano_e_media_type_sgp(
    provedor: MagicMock,
) -> None:
    """A consulta devolve falso como JSON booleano, sem envelope."""
    with patch(
        "apps.eol_autenticacao.services.recuperacao_senha.get_api_client"
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
    assert not provedor.method_calls


@override_settings(API_KEY="teste")
def test_preserva_erro_negocio() -> None:
    """Mantém o status e a mensagem do serviço responsável pela recuperação."""
    with patch(
        "apps.eol_autenticacao.services.recuperacao_senha.get_api_client"
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
        "apps.eol_autenticacao.services.recuperacao_senha.get_api_client"
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
        "apps.eol_autenticacao.services.recuperacao_senha.get_api_client"
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
        assert (
            schema["paths"][f"{BASE}{operacao}"]["post"]["security"]
            == operacao_sgp["security"]
            == [{"ApiKeyAuth": []}]
        )
    esquemas = schema["components"]["securitySchemes"]
    assert esquemas["ApiKeyAuth"]["name"] == "X-Identidade-Key"
    assert "ApiKeyLegado" not in esquemas
    assert not any(
        caminho.startswith("/api/v1/autenticacao/")
        for caminho in schema["paths"]
    )


@pytest.mark.parametrize("etapa", ["consultar", "reservar", "concluir"])
@override_settings(API_KEY="teste")
def test_timeout_nao_repete_alteracao(etapa: str, provedor: MagicMock) -> None:
    """Falhas antes da reserva impedem a troca; após a troca não a repetem."""

    def responder(
        rota: str, *, payload: dict, **kwargs: object
    ) -> httpx.Response:
        if rota.endswith("/" + etapa):
            raise httpx.ReadTimeout("resposta perdida")
        return responder_ms(rota, payload=payload)

    with patch.object(recuperacao_senha, "get_api_client") as obter:
        obter.return_value.post.side_effect = responder
        resposta = APIClient().post(
            BASE + "AlterarSenha",
            {"Token": TOKEN, "Senha": "NovaSenha123"},
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 504
    assert provedor.alterar_senha.call_count == (
        1 if etapa == "concluir" else 0
    )


@pytest.mark.parametrize(
    ("etapa", "erro", "resultado", "motivo", "status"),
    [
        (
            "preparar_alteracao_senha",
            PoliticaSenhaIncompativelError,
            "rejeitada",
            "politica",
            502,
        ),
        (
            "preparar_alteracao_senha",
            ProvedorIndisponivelError,
            "rejeitada",
            "indisponivel",
            502,
        ),
        (
            "alterar_senha",
            SenhaNoHistoricoError,
            "rejeitada",
            "historico",
            401,
        ),
        ("alterar_senha", ProvedorIndisponivelError, "incerta", "", 502),
    ],
)
@override_settings(API_KEY="teste")
def test_gateway_informa_resultado_ao_token(
    etapa: str,
    erro: type[Exception],
    resultado: str,
    motivo: str,
    status: int,
    provedor: MagicMock,
) -> None:
    """Distingue rejeição confirmada de resultado incerto sem vazar o SDK."""
    getattr(provedor, etapa).side_effect = erro
    with patch.object(recuperacao_senha, "get_api_client") as obter:
        obter.return_value.post.side_effect = responder_ms
        resposta = APIClient().post(
            BASE + "AlterarSenha",
            {"Token": TOKEN, "Senha": "NovaSenha123"},
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == status
    conclusao = obter.return_value.post.call_args.kwargs["payload"]
    assert conclusao["resultado"] == resultado
    assert conclusao["motivo"] == motivo
    if etapa == "preparar_alteracao_senha":
        provedor.alterar_senha.assert_not_called()


@override_settings(API_KEY="teste")
def test_reserva_incompativel_impede_alteracao(provedor: MagicMock) -> None:
    """Uma resposta de reserva trocada não autoriza a escrita da senha."""
    with patch.object(recuperacao_senha, "get_api_client") as obter:
        obter.return_value.post.side_effect = [
            httpx.Response(200, json={"usuario_id": CONTA.id}),
            httpx.Response(
                200, json={"operacao_id": TOKEN, "usuario_id": "outra-conta"}
            ),
        ]
        resposta = APIClient().post(
            BASE + "AlterarSenha",
            {"Token": TOKEN, "Senha": "NovaSenha123"},
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 502
    provedor.preparar_alteracao_senha.assert_not_called()
    provedor.alterar_senha.assert_not_called()


@override_settings(API_KEY="teste")
def test_usuario_ausente_e_falha_do_provedor_sao_distintos(
    provedor: MagicMock,
) -> None:
    """Somente ausência confirmada é encaminhada como conta nula ao MS."""
    with patch.object(recuperacao_senha, "get_api_client") as obter:
        provedor.buscar_usuario_por_login.return_value = None
        obter.return_value.post.return_value = httpx.Response(
            400, json="Usuário ou RF não encontrado"
        )
        cliente = APIClient()
        argumentos = {
            "data": json.dumps("1234567"),
            "content_type": "application/json",
            "HTTP_X_API_KEY": "teste",
        }
        assert (
            cliente.post(
                BASE + "RecuperarSenha/usuario?sistema=1", **argumentos
            ).status_code
            == 400
        )
        assert (
            obter.return_value.post.call_args.kwargs["payload"]["conta"]
            is None
        )
        obter.return_value.post.reset_mock()
        provedor.buscar_usuario_por_login.side_effect = (
            ProvedorIndisponivelError
        )
        assert (
            cliente.post(
                BASE + "RecuperarSenha/usuario?sistema=1", **argumentos
            ).status_code
            == 502
        )
        obter.return_value.post.assert_not_called()


@override_settings(API_KEY="teste")
def test_dados_do_formulario_nao_substituem_conta_do_token(
    provedor: MagicMock,
) -> None:
    """Campos adicionais do cliente não alteram a identidade autorizada."""
    with patch.object(recuperacao_senha, "get_api_client") as obter:
        obter.return_value.post.side_effect = responder_ms
        resposta = APIClient().post(
            BASE + "AlterarSenha",
            {
                "Token": TOKEN,
                "Senha": "NovaSenha123",
                "usuario_id": "outro",
                "contexto": "outro",
                "conta": "outro",
            },
            HTTP_X_API_KEY="teste",
        )
    assert resposta.status_code == 200
    reserva = obter.return_value.post.call_args_list[1].kwargs["payload"]
    assert reserva["conta"]["id"] == CONTA.id
    assert reserva["contexto"] == "identidade-local"
    provedor.alterar_senha.assert_called_once_with(CONTA.id, "NovaSenha123")
