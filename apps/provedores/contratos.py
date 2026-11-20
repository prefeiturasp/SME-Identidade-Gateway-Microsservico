"""Contrato de identidade independente da implementação do provedor."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class UsuarioIdentidade:
    """Dados da conta usados pelas regras de recuperação.

    Attributes:
        id: Identificador da conta no contexto do provedor.
        login: Login cadastrado da conta.
        nome: Nome completo para apresentação ao usuário.
        email: Endereço cadastrado, quando disponível.
        ativo: Indica se a conta está habilitada.
        rf: Registro funcional, quando disponível.
        cpf: CPF, quando disponível.
    """

    id: str
    login: str
    nome: str
    email: str | None
    ativo: bool
    rf: str | None = None
    cpf: str | None = None


class ProvedorIdentidade(Protocol):
    """Operações exigidas pelo fluxo de recuperação de senha."""

    @property
    def contexto(self) -> str:
        """Retorna o contexto que separa as contas do provedor.

        Returns:
            Identificador estável do contexto de identidade.
        """
        ...

    def buscar_usuario_por_login(self, login: str) -> UsuarioIdentidade | None:
        """Busca uma conta pelo login exato.

        Args:
            login: Login cadastrado, sem busca alternativa por atributos.

        Returns:
            Conta normalizada ou None quando não encontrada.
        """
        ...

    def obter_usuario(self, usuario_id: str) -> UsuarioIdentidade:
        """Consulta uma conta pelo identificador persistido.

        Args:
            usuario_id: Identificador da conta no contexto atual.

        Returns:
            Conta normalizada pelo adaptador.

        Raises:
            ContaNaoEncontradaError: Se a conta não existir.
        """
        ...

    def preparar_alteracao_senha(
        self, usuario_id: str, historico_minimo: int
    ) -> None:
        """Verifica a política e prepara uma senha definitiva.

        Args:
            usuario_id: Identificador da conta.
            historico_minimo: Quantidade mínima de senhas no histórico.

        Raises:
            PoliticaSenhaIncompativelError: Se o histórico não for atendido.
        """
        ...

    def alterar_senha(self, usuario_id: str, senha: str) -> None:
        """Define uma senha definitiva para a conta.

        Args:
            usuario_id: Identificador da conta.
            senha: Nova credencial, já validada pelas regras da aplicação.

        Raises:
            AlteracaoSenhaRejeitadaError: Se o provedor confirmar rejeição.
            ProvedorIndisponivelError: Se o resultado não puder ser confirmado.
        """
        ...
