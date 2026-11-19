"""Adaptador do contrato legado para a recuperação no MS-Identidade."""

import uuid
from typing import Any, cast
from urllib.parse import urlsplit

import httpx
from django.conf import settings

from apps.core.api_clients import get_api_client


class RecuperacaoSenhaError(Exception):
    """Representa uma falha na operação de recuperação.

    Attributes:
        status: Código HTTP recebido do MS-Token ou definido para a
            falha de comunicação.
    """

    def __init__(self, mensagem: str, status: int = 400) -> None:
        """Inicializa o erro com a mensagem e o status da operação.

        Args:
            mensagem: Mensagem retornada ao consumidor do contrato legado.
            status: Código HTTP associado à falha.
        """
        super().__init__(mensagem)
        self.status = status


def normalizar_uuid(token: object) -> str | None:
    """Normaliza um UUID para sua representação textual canônica.

    A conversão verifica somente o formato. A validade e o consumo da
    solicitação são verificados pelo MS-Token.

    Args:
        token: Valor recebido como código de recuperação.

    Returns:
        UUID normalizado ou None quando o formato for inválido.
    """
    try:
        return str(uuid.UUID(str(token)))
    except (ValueError, TypeError, AttributeError):
        return None


def _chamar(
    operacao: str, corpo: dict | str, params: dict | None = None
) -> Any:
    """Executa uma operação de recuperação na API do MS-Token.

    Args:
        operacao: Sufixo da rota de recuperação no serviço de destino.
        corpo: Dados enviados como JSON, conforme o contrato interno.
        params: Parâmetros de query string ou None quando não houver.

    Returns:
        Corpo JSON da resposta de sucesso do MS-Token.

    Raises:
        RecuperacaoSenhaError: Se o destino retornar erro, uma resposta
            inválida ou houver falha de comunicação. O status é 504 para
            timeout, 502 para outras falhas de comunicação e o status
            original para respostas de erro do serviço.
    """
    prefixo = (
        "/api/v1"
        if urlsplit(settings.TOKEN_MS_URL).path.rstrip("/")
        else "/identidade-token/api/v1"
    )
    try:
        resposta = get_api_client("token").post(
            f"{prefixo}/recuperacao-senha/{operacao}",
            payload=corpo,
            params=params,
        )
    except httpx.TimeoutException as erro:
        raise RecuperacaoSenhaError(
            "Serviço de identidade indisponível.", 504
        ) from erro
    except httpx.HTTPError as erro:
        raise RecuperacaoSenhaError(
            "Serviço de identidade indisponível.", 502
        ) from erro
    try:
        resultado = resposta.json()
    except ValueError as erro:
        raise RecuperacaoSenhaError(
            "Resposta inválida do serviço de identidade.", 502
        ) from erro
    if resposta.status_code != 200:
        raise RecuperacaoSenhaError(
            (
                resultado
                if isinstance(resultado, str)
                else "Não foi possível concluir a recuperação de senha."
            ),
            resposta.status_code,
        )
    return resultado


def solicitar(login: str, sistema: int) -> str:
    """Encaminha a solicitação de recuperação ao MS-Token.

    Args:
        login: Login cadastrado do usuário.
        sistema: Código do sistema no cadastro de recuperação.

    Returns:
        E-mail de destino informado pelo MS-Token após o envio do link.

    Raises:
        RecuperacaoSenhaError: Se a solicitação for rejeitada ou a
            comunicação com o MS-Token falhar.
    """
    return cast(
        str, _chamar("RecuperarSenha/usuario", login, {"sistema": sistema})
    )


def validar(token: object) -> bool:
    """Consulta a validade do código de recuperação no MS-Token.

    Args:
        token: Código de recuperação recebido do consumidor.

    Returns:
        True se o código ainda puder ser usado; False se for inexistente,
        expirado, substituído ou já utilizado.

    Raises:
        RecuperacaoSenhaError: Se o MS-Token rejeitar a consulta ou houver
            falha de comunicação. Essas falhas não são convertidas em False.
    """
    return cast(bool, _chamar("RecuperarSenha/token/validar", str(token)))


def alterar(token: str, senha: str) -> str:
    """Encaminha a definição da nova senha ao MS-Token.

    Args:
        token: Código de recuperação associado à conta.
        senha: Nova senha informada pelo usuário.

    Returns:
        Login informado pelo MS-Token após a alteração da senha.

    Raises:
        RecuperacaoSenhaError: Se o código ou a senha forem rejeitados ou
            houver falha de comunicação.
    """
    return cast(str, _chamar("AlterarSenha", {"Token": token, "Senha": senha}))
