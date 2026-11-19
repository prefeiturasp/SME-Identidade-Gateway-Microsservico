"""Testes das regras de consulta sem dependência de SDK ou framework web."""

from collections.abc import Iterable
from dataclasses import dataclass, field

import pytest

from apps.autenticacao.services import (
    ConsultaUsuariosIndisponivelError,
    UsuarioNaoEncontradoError,
    existe_email_em_outro_usuario,
)


@dataclass
class ConsultaUsuariosEmMemoria:
    """Implementa as consultas com contas e e-mails em memória."""

    ids_por_login: dict[str, str] = field(
        default_factory=lambda: {"1234567": "conta-atual"}
    )
    ids_por_email: dict[str, list[str]] = field(default_factory=dict)
    falha_em: str | None = None

    def obter_id_por_login(self, login: str) -> str | None:
        if self.falha_em == "login":
            raise ConsultaUsuariosIndisponivelError
        return self.ids_por_login.get(login)

    def listar_ids_por_email(self, email: str) -> Iterable[str]:
        if self.falha_em == "email":
            raise ConsultaUsuariosIndisponivelError
        return iter(self.ids_por_email.get(email, []))


@pytest.mark.parametrize(
    ("ids", "esperado"),
    [
        ([], False),
        (["conta-atual"], False),
        (["outra-conta"], True),
        (["conta-atual", "outra-conta"], True),
        (["outra-conta", "conta-atual"], True),
    ],
)
def test_exclui_a_conta_pelo_id(ids: list[str], esperado: bool) -> None:
    """Exclui a própria conta mesmo quando o ID é diferente do login."""
    usuarios = ConsultaUsuariosEmMemoria(
        ids_por_email={"teste@example.com": ids}
    )

    resultado = existe_email_em_outro_usuario(
        "1234567", "teste@example.com", usuarios
    )

    assert resultado is esperado


def test_login_inexistente_interrompe_antes_da_consulta_de_email() -> None:
    """Não consulta duplicidade sem identificar a conta a excluir."""
    usuarios = ConsultaUsuariosEmMemoria(falha_em="email")

    with pytest.raises(UsuarioNaoEncontradoError):
        existe_email_em_outro_usuario(
            "inexistente", "teste@example.com", usuarios
        )


@pytest.mark.parametrize("etapa", ["login", "email"])
def test_falha_do_provedor_nao_vira_email_disponivel(etapa: str) -> None:
    """Uma consulta incompleta preserva a indisponibilidade."""
    usuarios = ConsultaUsuariosEmMemoria(falha_em=etapa)

    with pytest.raises(ConsultaUsuariosIndisponivelError):
        existe_email_em_outro_usuario("1234567", "teste@example.com", usuarios)
