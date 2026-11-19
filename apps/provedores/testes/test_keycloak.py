"""Verifica a tradução entre a API do Keycloak e o contrato de identidade."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from keycloak.exceptions import (
    KeycloakConnectionError,
    KeycloakGetError,
    KeycloakPutError,
)

from apps.provedores.excecoes import (
    AlteracaoSenhaRejeitadaError,
    ContaNaoEncontradaError,
    PoliticaSenhaIncompativelError,
    ProvedorIndisponivelError,
    SenhaForaPoliticaError,
    SenhaNoHistoricoError,
)
from apps.provedores.fabrica import obter_provedor_identidade
from apps.provedores.keycloak import ProvedorKeycloak


@pytest.fixture
def admin() -> Iterator[MagicMock]:
    """Isola a fronteira de rede do adaptador."""
    with patch("apps.provedores.keycloak.obter_admin_keycloak") as obter:
        yield obter.return_value


def test_alteracao_nao_habilita_repeticao_de_transporte() -> None:
    """Não repete uma escrita cuja resposta pode ter sido perdida."""
    with patch("apps.provedores.keycloak.obter_admin_keycloak") as obter:
        ProvedorKeycloak().alterar_senha("conta-1", "NovaSenha123")
    obter.assert_called_once_with(max_retries=0)


def test_conta_normalizada_sem_campos_do_sdk(admin: MagicMock) -> None:
    """Expõe dados de domínio e mantém a consulta exata pelo login."""
    admin.get_users.return_value = [
        {
            "id": "conta-1",
            "username": "LOGIN",
            "firstName": "Maria",
            "lastName": "Silva",
            "email": "maria@example.com",
            "enabled": True,
            "attributes": {"rf": ["1234567"], "cpf": "12345678901"},
        }
    ]
    conta = ProvedorKeycloak().buscar_usuario_por_login("login")
    assert conta is not None
    assert (conta.id, conta.login, conta.nome, conta.ativo) == (
        "conta-1",
        "LOGIN",
        "Maria Silva",
        True,
    )
    assert conta.email == "maria@example.com"
    assert conta.rf == "1234567"
    assert conta.cpf == "12345678901"
    admin.get_users.assert_called_once_with(
        query={"username": "login", "exact": True}
    )


@pytest.mark.parametrize(
    ("status", "esperado"),
    [(404, ContaNaoEncontradaError), (503, ProvedorIndisponivelError)],
)
def test_falha_de_conta_tem_erro_neutro(
    admin: MagicMock, status: int, esperado: type[Exception]
) -> None:
    """Distingue ausência de conta de indisponibilidade do provedor."""
    admin.get_user.side_effect = KeycloakGetError(response_code=status)
    with pytest.raises(esperado):
        ProvedorKeycloak().obter_usuario("conta-1")


@pytest.mark.parametrize(
    ("status", "resposta", "esperado"),
    [
        (400, b"invalidPasswordHistoryMessage", SenhaNoHistoricoError),
        (400, b"invalidPasswordMinLengthMessage", SenhaForaPoliticaError),
        (400, b"outra rejeicao", AlteracaoSenhaRejeitadaError),
        (503, b"invalidPasswordHistoryMessage", ProvedorIndisponivelError),
    ],
)
def test_traduz_rejeicao_confirmada_da_senha(
    admin: MagicMock,
    status: int,
    resposta: bytes,
    esperado: type[Exception],
) -> None:
    """Só interpreta rejeições de senha quando o provedor confirma 400."""
    admin.set_user_password.side_effect = KeycloakPutError(
        response_code=status, response_body=resposta
    )
    with pytest.raises(esperado):
        ProvedorKeycloak().alterar_senha("conta-1", "NovaSenha123")


def test_timeout_nao_e_tratado_como_rejeicao(admin: MagicMock) -> None:
    """Resultado incerto permanece distinto de senha não aplicada."""
    admin.set_user_password.side_effect = KeycloakConnectionError("timeout")
    with pytest.raises(ProvedorIndisponivelError):
        ProvedorKeycloak().alterar_senha("conta-1", "NovaSenha123")


@pytest.mark.parametrize("politica", ["", "passwordHistory(4)"])
def test_politica_insuficiente_nao_prepara_conta(
    admin: MagicMock, politica: str
) -> None:
    """A aplicação exige cinco senhas sem depender da sintaxe do provedor."""
    admin.get_realm.return_value = {"passwordPolicy": politica}
    with pytest.raises(PoliticaSenhaIncompativelError):
        ProvedorKeycloak().preparar_alteracao_senha("conta-1", 5)
    admin.update_user.assert_not_called()


@override_settings(PROVEDOR_IDENTIDADE="adaptador_inexistente.Provedor")
def test_configuracao_invalida_nao_expoe_erro_de_importacao() -> None:
    """Uma configuração indisponível usa o erro neutro da aplicação."""
    with pytest.raises(ProvedorIndisponivelError):
        obter_provedor_identidade()
