"""Regras de consulta de usuários independentes do provedor de identidade."""

from collections.abc import Iterable
from typing import Protocol


class ConsultaUsuarios(Protocol):
    """Operações de leitura."""

    def obter_id_por_login(self, login: str) -> str | None:
        """Retorna o ID da conta ou None quando o login não existir."""
        ...

    def listar_ids_por_email(self, email: str) -> Iterable[str]:
        """Retorna os IDs de todas as contas com o e-mail completo."""
        ...


class UsuarioNaoEncontradoError(Exception):
    """O login informado não identifica uma conta."""

    def __init__(self, message: str = "Usuário não encontrado.") -> None:
        super().__init__(message)


class ConsultaUsuariosIndisponivelError(Exception):
    """Não foi possível consultar o provedor de identidade."""

    def __init__(
        self, message: str = "Provedor de identidade indisponível."
    ) -> None:
        super().__init__(message)


def existe_email_em_outro_usuario(
    login: str,
    email: str,
    usuarios: ConsultaUsuarios,
) -> bool:
    """Verifica se o e-mail pertence a uma conta diferente da informada.

    Args:
        login: RF ou CPF do usuário que deve ser excluído da busca.
        email: E-mail completo a consultar.
        usuarios: Implementação das consultas ao provedor de identidade.

    Returns:
        True se outra conta possuir o e-mail; False caso contrário.

    Raises:
        UsuarioNaoEncontradoError: Se não for possível identificar a conta.
        ConsultaUsuariosIndisponivelError: Se o provedor de identidade falhar.
    """
    usuario_id = usuarios.obter_id_por_login(login)
    if usuario_id is None:
        raise UsuarioNaoEncontradoError

    return any(
        outro_id != usuario_id
        for outro_id in usuarios.listar_ids_por_email(email)
    )
