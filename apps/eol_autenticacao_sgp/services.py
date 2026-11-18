"""Serviços dos endpoints legados de autenticação do SGP."""

from __future__ import annotations

import re
from typing import Any

from apps.core.api_clients import get_api_client

_EMAIL_REGEX = re.compile(
    r"\A(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)\Z",
    re.IGNORECASE,
)


class ConsultaCoreSSOError(Exception):
    """Representa uma falha na consulta ao CoreSSO."""


class IntegracaoETLError(Exception):
    """Representa uma falha na integração com o MS-ETL."""


class ConsultaAbrangenciaError(Exception):
    """Representa uma falha na consulta ao MS-Abrangência."""


def _buscar_dados_usuario_etl(
    login: str,
) -> dict[str, Any] | None:
    """Consulta os dados de um usuário no MS-ETL.

    Args:
        login: Login do usuário.

    Returns:
        Dados cadastrais ou None quando não encontrado.

    Raises:
        ConsultaCoreSSOError: Se ocorrer uma falha na consulta ao CoreSSO.
        IntegracaoETLError: Se a resposta do MS-ETL for inválida.
    """
    url_etl = f"/api/v1/etl/coresso/usuarios/{login}/dados/"

    resposta = get_api_client("etl").get(url_etl)

    if resposta.status_code == 204:
        return None

    if resposta.status_code == 503:
        try:
            erro = resposta.json()
        except ValueError:
            erro = None

        if (
            isinstance(erro, dict)
            and erro.get("codigo") == "ERRO_CONSULTA_CORESSO"
        ):
            raise ConsultaCoreSSOError("Falha na consulta ao CoreSSO.")

    if resposta.status_code != 200:
        raise IntegracaoETLError(
            f"MS-ETL retornou HTTP {resposta.status_code}."
        )

    try:
        dados = resposta.json()
    except ValueError as exc:
        raise IntegracaoETLError("Resposta JSON inválida do MS-ETL.") from exc

    if not isinstance(dados, dict):
        raise IntegracaoETLError("Resposta do MS-ETL deve ser um objeto JSON.")

    return dados


def _buscar_dre_vigente(login: str) -> str | None:
    """Consulta a DRE vigente de um usuário.

    Args:
        login: Registro funcional do usuário.

    Returns:
        Código da DRE ou None quando não encontrado.

    Raises:
        ConsultaAbrangenciaError: Se a resposta do serviço for inválida.
    """
    url_abrangencia = f"/api/abrangencia/usuarios/{login}/dre-vigente"

    resposta = get_api_client("abrangencia").get(url_abrangencia)

    if resposta.status_code == 204:
        return None

    if resposta.status_code != 200:
        raise ConsultaAbrangenciaError(
            f"MS-Abrangência retornou HTTP {resposta.status_code}."
        )

    try:
        dados = resposta.json()
    except ValueError as exc:
        raise ConsultaAbrangenciaError(
            "Resposta JSON inválida do MS-Abrangência."
        ) from exc

    codigo = dados.get("dreCodigo")

    if codigo is None:
        return None

    return str(codigo)


def _login_eh_int32(login: str) -> bool:
    """Verifica se o login pode ser convertido em Int32.

    Args:
        login: Login do usuário.

    Returns:
        True quando o login representa um inteiro de 32 bits.
    """
    valor = login.strip()

    if re.fullmatch(r"[+-]?\d+", valor, flags=re.ASCII) is None:
        return False

    try:
        numero = int(valor)
    except ValueError:
        return False

    return -(2**31) <= numero < 2**31


def _email_valido(email: str | None) -> bool:
    """Valida o formato de um endereço de e-mail.

    Args:
        email: Endereço de e-mail.

    Returns:
        True quando o e-mail possui formato válido.
    """
    return bool(
        email and not email.isspace() and _EMAIL_REGEX.fullmatch(email)
    )


class ServicoDadosUsuario:
    """Consulta e compõe os dados cadastrais de um usuário."""

    def carregar(
        self,
        login: str,
    ) -> dict[str, str | bool | None] | None:
        """Carrega os dados do usuário pelo login.

        Args:
            login: Login do usuário.

        Returns:
            Dados do usuário ou None quando não encontrados.
        """
        usuario = _buscar_dados_usuario_etl(login)

        if usuario is not None:
            email = usuario["email"]
            email_valido = _email_valido(email)

            return {
                "cpf": usuario["cpf"],
                "nome": usuario["nome"],
                "codigoRf": (login if _login_eh_int32(login) else None),
                "email": email if email_valido else None,
                "dreCodigo": None,
                "emailValido": email_valido,
            }

        dre_codigo = _buscar_dre_vigente(login)

        if dre_codigo is None:
            return None

        return {
            "cpf": None,
            "nome": None,
            "codigoRf": None,
            "email": None,
            "dreCodigo": dre_codigo,
            "emailValido": False,
        }
