"""Serviços dos endpoints legados de autenticação EOL."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID

from django.conf import settings

from apps.autenticacao import keycloak_admin
from apps.core.api_clients import get_api_client
from apps.eol_autenticacao.api.serializers import (
    DadosFuncionaisExternosSerializer,
)

_MENSAGEM_USUARIO_NAO_ENCONTRADO = "Usuário não encontrado."


class CodigoSistemaInvalidoError(Exception):
    """Indica que o código do sistema informado é zero."""


class UsuarioExternoNaoEncontradoError(Exception):
    """Indica usuário não localizado ou inelegível no Keycloak."""


class CredenciaisExternasInvalidasError(Exception):
    """Indica credenciais inválidas para a autenticação externa."""


class ConsultaKeycloakExternaError(Exception):
    """Indica falha técnica na autenticação ou consulta ao Keycloak."""


class DadosFuncionaisExternosError(Exception):
    """Indica falha na consulta de dados funcionais à Abrangência."""


def _atributo_coresso(
    registro: dict[str, Any],
    nome: str,
) -> str | None:
    """Obtém um atributo do Keycloak como texto.

    Args:
        registro: Representação de usuário, client ou role do Keycloak.
        nome: Nome do atributo desejado.

    Returns:
        Primeiro valor do atributo ou ``None`` quando ausente.
    """
    atributos = registro.get("attributes") or {}
    valor = atributos.get(nome)

    if isinstance(valor, list):
        valor = valor[0] if valor else None

    return str(valor) if valor is not None else None


def _obter_grupo_id_coresso(
    admin: Any,
    client_uuid: str,
    role: dict[str, Any],
    codigo_sistema: int,
) -> str | None:
    """Obtém o GUID do CoreSSO associado a uma role do Keycloak.

    Args:
        admin: Cliente administrativo do Keycloak.
        client_uuid: Identificador interno do client no Keycloak.
        role: Dados da role atribuída ao usuário.
        codigo_sistema: Código do sistema informado na requisição.

    Returns:
        GUID original do grupo ou ``None`` para roles não originárias
        do CoreSSO.

    Raises:
        ConsultaKeycloakExternaError: Se os metadados de uma role
            CoreSSO estiverem ausentes, inconsistentes ou inválidos.
    """
    atributos = role

    if _atributo_coresso(role, "coresso_gru_id") is None:
        atributos = admin.get_client_role(
            client_uuid,
            str(role["name"]),
        )

    grupo_id = _atributo_coresso(atributos, "coresso_gru_id")

    if grupo_id is None:
        descricao = str(atributos.get("description", ""))

        if "CoreSSO gru_id=" in descricao:
            raise ConsultaKeycloakExternaError(
                "Role CoreSSO sem o atributo coresso_gru_id."
            )

        return None

    if _atributo_coresso(atributos, "coresso_sis_id") != str(codigo_sistema):
        raise ConsultaKeycloakExternaError(
            "Role vinculada a outro sistema CoreSSO."
        )

    try:
        return str(UUID(grupo_id))
    except ValueError as exc:
        raise ConsultaKeycloakExternaError(
            "Role com GUID CoreSSO inválido."
        ) from exc


def _obter_perfis_coresso(
    admin: Any,
    usuario_id: str,
    codigo_sistema: int,
) -> list[str]:
    """Recupera os GUIDs dos grupos no client do ambiente configurado.

    A seleção utiliza o ``coresso_sis_id`` e o mesmo sufixo de client
    definido pelo ETL. A ausência do sistema não impede o login.

    Args:
        admin: Cliente administrativo do Keycloak.
        usuario_id: Identificador UUID do usuário no Keycloak.
        codigo_sistema: Identificador numérico do sistema no CoreSSO.

    Returns:
        Lista de GUIDs dos grupos do sistema ou lista vazia quando
        o sistema não existir ou o usuário não possuir roles.

    Raises:
        ConsultaKeycloakExternaError: Se houver ambiguidade de client,
            configuração divergente ou metadados inválidos de roles.
    """
    sufixo = (
        (getattr(settings, "KEYCLOAK_SUFIXO_CLIENT", None) or "prod")
        .strip()
        .lower()
    )

    clientes_sistema = [
        cliente
        for cliente in admin.get_clients()
        if _atributo_coresso(cliente, "coresso_sis_id") == str(codigo_sistema)
    ]

    if not clientes_sistema:
        return []

    correspondentes = [
        cliente
        for cliente in clientes_sistema
        if str(cliente.get("clientId", "")).lower().endswith(f"-{sufixo}")
    ]

    if not correspondentes:
        raise ConsultaKeycloakExternaError(
            "Client do sistema não encontrado no ambiente configurado."
        )

    if len(correspondentes) > 1:
        raise ConsultaKeycloakExternaError(
            "Mais de um client do sistema encontrado no ambiente."
        )

    client_uuid = str(correspondentes[0]["id"])
    roles = admin.get_client_roles_of_user(usuario_id, client_uuid)
    perfis: list[str] = []

    for role in roles:
        grupo_id = _obter_grupo_id_coresso(
            admin,
            client_uuid,
            role,
            codigo_sistema,
        )

        if grupo_id is not None:
            perfis.append(grupo_id)

    return perfis


def _buscar_dados_funcionais_externos(login: str) -> dict[str, Any]:
    """Obtém os dados funcionais para o retorno da autenticação.

    Args:
        login: Login do usuário no sistema legado.

    Returns:
        Dicionário com cargos, cargos sobrepostos, unidades de lotação
        e unidade de exercício. Os campos podem ser nulos.

    Raises:
        DadosFuncionaisExternosError: Se o serviço não retornar HTTP
            200 ou enviar dados incompatíveis com o contrato.
    """
    caminho = (
        f"/api/abrangencia/usuarios/{quote(login, safe='')}/"
        "dados-funcionais-autenticacao-externa"
    )
    resposta = get_api_client("abrangencia").get(caminho)

    if resposta.status_code != 200:
        raise DadosFuncionaisExternosError(
            f"MS-Abrangência retornou HTTP {resposta.status_code}."
        )

    try:
        dados = resposta.json()
    except ValueError as exc:
        raise DadosFuncionaisExternosError(
            "MS-Abrangência retornou JSON inválido."
        ) from exc

    serializer = DadosFuncionaisExternosSerializer(data=dados)

    if not serializer.is_valid():
        raise DadosFuncionaisExternosError(
            "MS-Abrangência retornou dados funcionais inválidos."
        )

    return dict(serializer.validated_data)


def _validar_senha_externa(
    username: str,
    senha: str | None,
) -> dict[str, Any]:
    """Autentica por meio do serviço compartilhado do Gateway.

    Args:
        username: Login informado para autenticação no Keycloak.
        senha: Senha informada na requisição.

    Returns:
        Dados cadastrais e identificador do usuário autenticado.

    Raises:
        CredenciaisExternasInvalidasError: Se a senha for inválida.
        UsuarioExternoNaoEncontradoError: Se o usuário não existir.
        ConsultaKeycloakExternaError: Se ocorrer falha técnica ou
            erro de autenticação não equivalente a senha incorreta.
    """
    try:
        resultado = keycloak_admin.autenticar(username, senha or "")
    except Exception as exc:
        raise ConsultaKeycloakExternaError(
            "Falha ao autenticar usuário no Keycloak."
        ) from exc

    if resultado.get("autenticado") is True:
        if not senha:
            raise CredenciaisExternasInvalidasError(
                "Usuário ou senha incorretos."
            )

        return resultado

    erro = str(resultado.get("erro") or "")

    if erro == keycloak_admin.ERRO_USUARIO_NAO_ENCONTRADO:
        raise UsuarioExternoNaoEncontradoError(
            _MENSAGEM_USUARIO_NAO_ENCONTRADO
        )

    detalhe = erro.casefold()

    if (
        not senha
        or "invalid user credentials" in detalhe
        or "invalid username or password" in detalhe
    ):
        raise CredenciaisExternasInvalidasError("Usuário ou senha incorretos.")

    raise ConsultaKeycloakExternaError(
        "Keycloak não concluiu a autenticação do usuário."
    )


class ServicoAutenticacaoExterna:
    """Orquestra a autenticação externa compatível com o EOL legado."""

    def autenticar(
        self,
        usuario: str | None,
        senha: str | None,
        codigo_sistema: int,
    ) -> dict[str, Any]:
        """Autentica o usuário e compõe o retorno da API legada.

        Args:
            usuario: Login informado pelo consumidor externo.
            senha: Senha informada pelo consumidor externo.
            codigo_sistema: Código do sistema para seleção de perfis.

        Returns:
            Dicionário com os dez campos do retorno legado, usando
            o UUID do Keycloak como ``usuarioId``.

        Raises:
            CodigoSistemaInvalidoError: Se o código do sistema for zero.
            UsuarioExternoNaoEncontradoError: Se a conta não existir
                ou estiver desabilitada.
            CredenciaisExternasInvalidasError: Se a senha for inválida.
            DadosFuncionaisExternosError: Se falhar a consulta funcional.
            ConsultaKeycloakExternaError: Se falhar a comunicação com
                o Keycloak ou a recuperação dos perfis.
        """
        if codigo_sistema == 0:
            raise CodigoSistemaInvalidoError("Informe o código do sistema.")

        if not usuario:
            raise UsuarioExternoNaoEncontradoError(
                _MENSAGEM_USUARIO_NAO_ENCONTRADO
            )

        # Preserva a ordem de consulta dos dados funcionais do legado.
        funcionais = _buscar_dados_funcionais_externos(usuario)

        resultado = _validar_senha_externa(usuario, senha)

        if resultado.get("ativo") is not True:
            raise UsuarioExternoNaoEncontradoError(
                _MENSAGEM_USUARIO_NAO_ENCONTRADO
            )

        try:
            admin = keycloak_admin.obter_admin_keycloak()
            perfis = _obter_perfis_coresso(
                admin,
                str(resultado["kc_user_id"]),
                codigo_sistema,
            )
        except ConsultaKeycloakExternaError:
            raise
        except Exception as exc:
            raise ConsultaKeycloakExternaError(
                "Falha ao consultar os perfis no Keycloak."
            ) from exc

        return {
            "usuarioId": str(resultado["kc_user_id"]),
            "nome": resultado.get("nome"),
            "codigoRf": usuario,
            "numeroDocumento": resultado.get("cpf"),
            "email": resultado.get("email"),
            "perfis": perfis,
            **funcionais,
        }
