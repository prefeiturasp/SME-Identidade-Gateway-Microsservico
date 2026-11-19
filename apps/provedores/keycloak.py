"""Adaptador que traduz o contrato de identidade para a API do Keycloak."""

import re
from collections.abc import Callable
from typing import Any, TypeVar, cast

from django.conf import settings
from keycloak.exceptions import (
    KeycloakError,
    KeycloakGetError,
    KeycloakPutError,
)

from apps.autenticacao.keycloak_admin import obter_admin_keycloak
from apps.provedores.contratos import UsuarioIdentidade
from apps.provedores.excecoes import (
    AlteracaoSenhaRejeitadaError,
    ContaNaoEncontradaError,
    PoliticaSenhaIncompativelError,
    ProvedorIndisponivelError,
    SenhaForaPoliticaError,
    SenhaNoHistoricoError,
)

T = TypeVar("T")


class ProvedorKeycloak:
    """Implementa as operações de identidade usando o SDK do Keycloak."""

    def __init__(self) -> None:
        """Inicializa o adaptador sem abrir conexão com o provedor."""
        self._admin: Any = None

    @property
    def contexto(self) -> str:
        """Retorna o realm usado como contexto de identidade.

        Returns:
            Nome do realm configurado para este adaptador.
        """
        return str(settings.KEYCLOAK_REALM)

    @property
    def _cliente(self) -> Any:
        """Obtém o cliente administrativo desta instância.

        Returns:
            Cliente do SDK, criado somente na primeira chamada remota.
        """
        if self._admin is None:
            self._admin = obter_admin_keycloak(max_retries=0)
        return self._admin

    def _executar(self, operacao: Callable[[], T]) -> T:
        """Traduz falhas técnicas sem expor exceções do SDK.

        Args:
            operacao: Chamada a executar no cliente do Keycloak.

        Returns:
            Resultado da operação administrativa.

        Raises:
            ProvedorIndisponivelError: Se houver falha técnica.
        """
        try:
            return operacao()
        except (KeycloakError, OSError) as erro:
            raise ProvedorIndisponivelError from erro

    def buscar_usuario_por_login(self, login: str) -> UsuarioIdentidade | None:
        """Consulta somente o username exato.

        Args:
            login: Login cadastrado da conta.

        Returns:
            Conta normalizada ou None se o username não existir.
        """
        usuarios = self._executar(
            lambda: self._cliente.get_users(
                query={"username": login, "exact": True}
            )
        )
        conta = next(
            (
                usuario
                for usuario in usuarios
                if usuario.get("username", "").casefold() == login.casefold()
            ),
            None,
        )
        return self._normalizar(conta) if conta is not None else None

    def _obter_conta(self, usuario_id: str) -> dict[str, Any]:
        """Consulta o cadastro bruto e traduz a ausência de conta.

        Args:
            usuario_id: Identificador da conta no realm.

        Returns:
            Cadastro do Keycloak para uso interno do adaptador.

        Raises:
            ContaNaoEncontradaError: Se o provedor responder 404.
            ProvedorIndisponivelError: Se ocorrer outra falha técnica.
        """
        try:
            return cast(dict[str, Any], self._cliente.get_user(usuario_id))
        except KeycloakGetError as erro:
            if erro.response_code == 404:
                raise ContaNaoEncontradaError from erro
            raise ProvedorIndisponivelError from erro
        except (KeycloakError, OSError) as erro:
            raise ProvedorIndisponivelError from erro

    def obter_usuario(self, usuario_id: str) -> UsuarioIdentidade:
        """Consulta uma conta pelo ID persistido.

        Args:
            usuario_id: Identificador da conta no realm.

        Returns:
            Dados da conta convertidos para o contrato da aplicação.
        """
        return self._normalizar(self._obter_conta(usuario_id))

    def preparar_alteracao_senha(
        self, usuario_id: str, historico_minimo: int
    ) -> None:
        """Confere o histórico e remove apenas a troca obrigatória de senha.

        Args:
            usuario_id: Identificador da conta no realm.
            historico_minimo: Quantidade mínima de senhas anteriores.

        Raises:
            PoliticaSenhaIncompativelError: Se o histórico for insuficiente.
        """
        politica = self._executar(
            lambda: self._cliente.get_realm(self.contexto)
        ).get("passwordPolicy", "")
        historico = re.search(r"(?:^|\s)passwordHistory\((\d+)\)", politica)
        if not historico or int(historico[1]) < historico_minimo:
            raise PoliticaSenhaIncompativelError
        acoes = self._obter_conta(usuario_id).get("requiredActions", [])
        if "UPDATE_PASSWORD" in acoes:
            self._executar(
                lambda: self._cliente.update_user(
                    user_id=usuario_id,
                    payload={
                        "requiredActions": [
                            acao for acao in acoes if acao != "UPDATE_PASSWORD"
                        ]
                    },
                )
            )

    def alterar_senha(self, usuario_id: str, senha: str) -> None:
        """Define a senha e traduz rejeições confirmadas pelo Keycloak.

        Args:
            usuario_id: Identificador da conta no realm.
            senha: Nova credencial definitiva.

        Raises:
            AlteracaoSenhaRejeitadaError: Se a senha não tiver sido aplicada.
            ProvedorIndisponivelError: Se o resultado for incerto.
        """
        try:
            self._cliente.set_user_password(
                user_id=usuario_id, password=senha, temporary=False
            )
        except KeycloakPutError as erro:
            if erro.response_code != 400:
                raise ProvedorIndisponivelError from erro
            corpo = erro.response_body or b""
            resposta = (
                corpo.decode(errors="replace")
                if isinstance(corpo, bytes)
                else str(corpo)
            )
            if "invalidPasswordHistoryMessage" in resposta:
                raise SenhaNoHistoricoError from erro
            if "invalidPassword" in resposta:
                raise SenhaForaPoliticaError from erro
            raise AlteracaoSenhaRejeitadaError from erro
        except (KeycloakError, OSError) as erro:
            raise ProvedorIndisponivelError from erro

    @staticmethod
    def _normalizar(conta: dict[str, Any]) -> UsuarioIdentidade:
        """Traduz o cadastro do Keycloak para os dados da aplicação.

        Args:
            conta: Cadastro bruto devolvido pelo SDK.

        Returns:
            Conta sem campos específicos do Keycloak.
        """
        atributos = conta.get("attributes") or {}

        def atributo(nome: str) -> str | None:
            """Extrai um atributo textual, aceitando listas do Keycloak."""
            valor = atributos.get(nome)
            if isinstance(valor, list):
                valor = valor[0] if valor else None
            return valor if isinstance(valor, str) and valor else None

        return UsuarioIdentidade(
            id=str(conta["id"]),
            login=conta.get("username", ""),
            nome=" ".join(
                filter(None, [conta.get("firstName"), conta.get("lastName")])
            ),
            email=conta.get("email"),
            ativo=bool(conta.get("enabled", False)),
            rf=atributo("rf"),
            cpf=atributo("cpf"),
        )
