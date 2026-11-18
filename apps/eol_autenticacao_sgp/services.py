"""Serviços dos endpoints legados de autenticação do SGP."""

from __future__ import annotations

import re

from apps.autenticacao import keycloak_admin
from apps.core.api_clients import get_api_client

_EMAIL_REGEX = re.compile(
    r"\A(?:"
    r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r")\Z",
    re.IGNORECASE,
)


class ConsultaAbrangenciaError(Exception):
    """Indica uma falha na consulta à API de Abrangência."""


def _login_eh_int32(login: str) -> bool:
    """Verifica se o login pode ser convertido para Int32.

    Args:
        login: Login informado na consulta.

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
    """Valida o formato do e-mail conforme a regra do Legado.

    Args:
        email: Endereço de e-mail a validar.

    Returns:
        True quando o e-mail possui formato válido.
    """
    if not isinstance(email, str) or not email.strip():
        return False

    return _EMAIL_REGEX.fullmatch(email) is not None


def _buscar_dre_vigente(login: str) -> str | None:
    """Consulta a DRE vigente de um usuário no MS-Abrangência.

    Args:
        login: Login do usuário.

    Returns:
        Código da DRE vigente ou None quando não encontrada.

    Raises:
        ConsultaAbrangenciaError: Se a integração retornar erro
            ou dados fora do contrato esperado.
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
            "MS-Abrangência retornou JSON inválido."
        ) from exc

    if not isinstance(dados, dict):
        raise ConsultaAbrangenciaError(
            "MS-Abrangência retornou dados inválidos."
        )

    if dados.get("login") != login:
        raise ConsultaAbrangenciaError(
            "MS-Abrangência retornou um login divergente."
        )

    codigo = dados.get("dreCodigo")

    if (
        isinstance(codigo, bool)
        or not isinstance(codigo, str | int)
        or not str(codigo).strip()
    ):
        raise ConsultaAbrangenciaError(
            "MS-Abrangência retornou um código de DRE inválido."
        )

    return str(codigo)


class ServicoDadosUsuario:
    """Consulta os dados cadastrais e a DRE vigente de um usuário."""

    def carregar(self, login: str) -> dict | None:
        """Obtém os dados do Keycloak ou consulta a DRE vigente.

        Args:
            login: Login do usuário.

        Returns:
            Dados cadastrais do usuário ativo, dados da DRE vigente
            ou None quando nenhuma informação é encontrada.
        """
        usuario = keycloak_admin.obter_dados_usuario(login)

        if usuario is not None and usuario.get("ativo") is True:
            email = usuario.get("email")
            email_valido = _email_valido(email)

            return {
                "cpf": usuario.get("cpf"),
                "nome": usuario.get("nome"),
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
