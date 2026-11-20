"""Adaptador do contrato legado para a recuperação no MS-Identidade."""

import uuid
from dataclasses import asdict
from typing import Any, NoReturn, cast
from urllib.parse import urlsplit

import httpx
from django.conf import settings

from apps.core.api_clients import get_api_client
from apps.provedores.contratos import ProvedorIdentidade
from apps.provedores.excecoes import (
    AlteracaoSenhaRejeitadaError,
    ContaNaoEncontradaError,
    PoliticaSenhaIncompativelError,
    ProvedorIndisponivelError,
    SenhaForaPoliticaError,
    SenhaNoHistoricoError,
)
from apps.provedores.fabrica import obter_provedor_identidade

RESPOSTA_IDENTIDADE_INVALIDA = "Resposta inválida do serviço de identidade."
FALHA_RECUPERACAO_SENHA = "Não foi possível concluir a recuperação de senha."


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
            RESPOSTA_IDENTIDADE_INVALIDA, 502
        ) from erro
    if resposta.status_code != 200:
        raise RecuperacaoSenhaError(
            (
                resultado
                if isinstance(resultado, str)
                else FALHA_RECUPERACAO_SENHA
            ),
            resposta.status_code,
        )
    return resultado


def _provedor() -> ProvedorIdentidade:
    """Seleciona a integração de identidade usada pelo Gateway.

    Returns:
        Provedor configurado, sem comunicação com o MS-Token.

    Raises:
        RecuperacaoSenhaError: Se o adaptador não puder ser carregado.
    """
    try:
        return obter_provedor_identidade()
    except ProvedorIndisponivelError as erro:
        raise RecuperacaoSenhaError(FALHA_RECUPERACAO_SENHA, 502) from erro


def solicitar(login: str, sistema: int) -> str:
    """Consulta a conta e solicita o envio do link ao MS-Token.

    Args:
        login: Login exato cadastrado no provedor.
        sistema: Código do sistema no cadastro de recuperação.

    Returns:
        Endereço de e-mail informado pelo MS-Token após o envio.
    """
    provedor = _provedor()
    try:
        conta = provedor.buscar_usuario_por_login(login)
    except ProvedorIndisponivelError as erro:
        raise RecuperacaoSenhaError(FALHA_RECUPERACAO_SENHA, 502) from erro
    return cast(
        str,
        _chamar(
            "solicitacoes",
            {
                "login": login,
                "sistema": sistema,
                "contexto": provedor.contexto,
                "conta": asdict(conta) if conta else None,
            },
        ),
    )


def validar(token: object) -> bool:
    """Consulta a validade local do código sem acessar o provedor.

    Args:
        token: UUID recebido do consumidor.

    Returns:
        Validade informada pelo MS-Token, sem consumir o código.
    """
    return cast(
        bool,
        _chamar(
            "tokens/validar",
            {"token": str(token), "contexto": _provedor().contexto},
        ),
    )


def _informar_falha(
    contexto: str, operacao_id: str, resultado: str, motivo: str = ""
) -> NoReturn:
    """Registra a falha sem liberar operações cujo resultado seja incerto.

    Args:
        contexto: Contexto da identidade.
        operacao_id: Reserva emitida pelo MS-Token.
        resultado: Rejeição confirmada ou resultado incerto.
        motivo: Motivo neutro a ser convertido para o contrato legado.

    Raises:
        RecuperacaoSenhaError: Resultado de negócio ou falha de comunicação.
    """
    _chamar(
        "alteracoes/concluir",
        {
            "contexto": contexto,
            "operacao_id": operacao_id,
            "resultado": resultado,
            "motivo": motivo,
        },
    )
    raise RecuperacaoSenhaError(FALHA_RECUPERACAO_SENHA, 502)


def alterar(token: str, senha: str) -> str:
    """Orquestra a reserva, a alteração no provedor e a confirmação.

    Args:
        token: UUID da solicitação de recuperação.
        senha: Nova senha informada pelo usuário.

    Returns:
        Login confirmado pelo MS-Token após a troca.

    Raises:
        RecuperacaoSenhaError: Se a conta, a senha ou a comunicação falharem.
    """
    provedor = _provedor()
    contexto = provedor.contexto
    consulta = _chamar(
        "alteracoes/consultar", {"token": token, "contexto": contexto}
    )
    if not isinstance(consulta, dict) or not isinstance(
        consulta.get("usuario_id"), str
    ):
        raise RecuperacaoSenhaError(RESPOSTA_IDENTIDADE_INVALIDA, 502)
    try:
        conta = provedor.obter_usuario(consulta["usuario_id"])
    except ContaNaoEncontradaError as erro:
        raise RecuperacaoSenhaError(
            "Usuário ou senha incorretos.", 401
        ) from erro
    except ProvedorIndisponivelError as erro:
        raise RecuperacaoSenhaError(FALHA_RECUPERACAO_SENHA, 502) from erro
    operacao_id = str(uuid.uuid4())
    reserva = _chamar(
        "alteracoes/reservar",
        {
            "contexto": contexto,
            "token": token,
            "senha": senha,
            "conta": asdict(conta),
            "operacao_id": operacao_id,
        },
    )
    if (
        not isinstance(reserva, dict)
        or reserva.get("operacao_id") != operacao_id
        or reserva.get("usuario_id") != conta.id
    ):
        raise RecuperacaoSenhaError(RESPOSTA_IDENTIDADE_INVALIDA, 502)
    try:
        provedor.preparar_alteracao_senha(conta.id, historico_minimo=5)
    except PoliticaSenhaIncompativelError:
        _informar_falha(contexto, operacao_id, "rejeitada", "politica")
    except ContaNaoEncontradaError:
        _informar_falha(contexto, operacao_id, "rejeitada", "conta")
    except ProvedorIndisponivelError:
        # A chamada de alteração de senha ainda não foi iniciada.
        _informar_falha(contexto, operacao_id, "rejeitada", "indisponivel")
    try:
        provedor.alterar_senha(conta.id, senha)
    except SenhaNoHistoricoError:
        _informar_falha(contexto, operacao_id, "rejeitada", "historico")
    except SenhaForaPoliticaError:
        _informar_falha(contexto, operacao_id, "rejeitada", "padrao")
    except AlteracaoSenhaRejeitadaError:
        _informar_falha(contexto, operacao_id, "rejeitada", "indisponivel")
    except ProvedorIndisponivelError:
        _informar_falha(contexto, operacao_id, "incerta")
    return cast(
        str,
        _chamar(
            "alteracoes/concluir",
            {
                "contexto": contexto,
                "operacao_id": operacao_id,
                "resultado": "sucesso",
            },
        ),
    )
