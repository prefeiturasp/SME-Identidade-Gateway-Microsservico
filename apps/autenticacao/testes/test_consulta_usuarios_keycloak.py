"""Testes do adaptador do contrato de consulta para o Keycloak."""

from unittest.mock import MagicMock, patch

import pytest
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakError,
    KeycloakGetError,
)

from apps.autenticacao.keycloak_admin import ConsultaUsuariosKeycloak
from apps.autenticacao.services import ConsultaUsuariosIndisponivelError


@pytest.mark.parametrize(
    ("login", "buscas_sem_resultado"),
    [("username", 0), ("1234567", 1), ("12345678900", 2)],
)
@patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
def test_resolve_login_e_consulta_email_com_o_mesmo_cliente(
    obter_admin: MagicMock, login: str, buscas_sem_resultado: int
) -> None:
    """Inclui contas inativas e consulta e-mail sem limitar os resultados."""
    conta = {"id": "conta-atual", "username": "username"}
    outra = {
        "id": "outra-conta",
        "enabled": False,
        "emailVerified": False,
    }
    admin = obter_admin.return_value
    admin.get_users.side_effect = [[]] * buscas_sem_resultado + [
        [conta],
        [conta, outra],
    ]
    consulta = ConsultaUsuariosKeycloak()
    obter_admin.assert_not_called()

    assert consulta.obter_id_por_login(login) == "conta-atual"
    assert consulta.listar_ids_por_email("Email+SGP@Example.com") == [
        "conta-atual",
        "outra-conta",
    ]

    obter_admin.assert_called_once_with()
    admin.get_users.assert_called_with(
        query={"email": "Email+SGP@Example.com", "exact": True}
    )


@patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
def test_usuario_e_email_ausentes_nao_sao_falhas_do_provedor(
    obter_admin: MagicMock,
) -> None:
    """Ausência de resultados mantém os retornos do contrato."""
    obter_admin.return_value.get_users.return_value = []
    consulta = ConsultaUsuariosKeycloak()

    assert consulta.obter_id_por_login("inexistente") is None
    assert consulta.listar_ids_por_email("livre@example.com") == []


@pytest.mark.parametrize(
    ("etapa", "erro"),
    [
        ("cliente", KeycloakAuthenticationError("credencial interna")),
        ("login", KeycloakGetError("consulta falhou", response_code=404)),
        ("email", KeycloakConnectionError("timeout")),
    ],
)
@patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
def test_traduz_falhas_do_sdk_para_o_contrato_da_aplicacao(
    obter_admin: MagicMock, etapa: str, erro: KeycloakError
) -> None:
    """Traduz erros na criação do cliente e nas consultas."""
    if etapa == "cliente":
        obter_admin.side_effect = erro
    else:
        obter_admin.return_value.get_users.side_effect = erro
    consulta = ConsultaUsuariosKeycloak()

    with pytest.raises(ConsultaUsuariosIndisponivelError) as falha:
        if etapa == "email":
            consulta.listar_ids_por_email("teste@example.com")
        else:
            consulta.obter_id_por_login("1234567")

    assert falha.value.__cause__ is erro
