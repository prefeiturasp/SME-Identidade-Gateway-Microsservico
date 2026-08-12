"""Cliente Keycloak Admin para gestão de credenciais.

Reaproveita o mesmo padrão de conexão do SME-Identidade-ETL
(``apps/controle_etl/orquestrador_kc.py:obter_admin_keycloak``),
mantendo um único jeito de instanciar ``KeycloakAdmin`` na
plataforma SME-Identidade.

As rotas de recuperação/alteração de senha e alteração de e-mail
delegam integralmente ao Keycloak — não reimplementam geração de
token de recuperação nem envio de e-mail, usam os mecanismos nativos
(``send_update_account``, ``set_user_password``) já providos pelo
Keycloak, evitando duplicar lógica de segurança sensível.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from django.conf import settings

ERRO_USUARIO_NAO_ENCONTRADO = "usuário não encontrado"


def obter_admin_keycloak() -> Any:
    """Retorna um cliente Keycloak Admin autenticado.

    Returns:
        Instância de ``KeycloakAdmin`` conectada ao realm
        configurado em ``settings.KEYCLOAK_REALM``.
    """
    from keycloak import KeycloakAdmin

    return KeycloakAdmin(
        server_url=settings.KEYCLOAK_URL_SERVIDOR,
        username=settings.KEYCLOAK_USUARIO_ADMIN,
        password=settings.KEYCLOAK_SENHA_ADMIN,
        realm_name=settings.KEYCLOAK_REALM,
        user_realm_name="master",
        verify=settings.KEYCLOAK_VERIFICAR_SSL,
    )


def _resolver_user_id(admin: Any, login: str) -> str:
    """Resolve o ``user_id`` do Keycloak a partir do login informado.

    Usa ``buscar_usuario_por_login`` (RF/CPF/e-mail/username) em vez
    de ``admin.get_user_id`` (só busca por username exato e retorna
    ``None``, sem lançar exceção, quando não encontra — o que faria
    as rotas de credencial chamarem o Keycloak com ``user_id=None``
    em vez de responder 404).

    Args:
        admin: Cliente KeycloakAdmin autenticado.
        login: RF, CPF, e-mail ou username do usuário.

    Returns:
        O ``id`` do usuário no Keycloak.

    Raises:
        KeycloakGetError: Se o usuário não existir no realm.
    """
    from keycloak.exceptions import KeycloakGetError

    conta = buscar_usuario_por_login(admin, login)
    if not conta:
        raise KeycloakGetError(ERRO_USUARIO_NAO_ENCONTRADO)
    return str(conta["id"])


def disparar_redefinicao_senha(login: str) -> None:
    """Dispara o e-mail nativo do Keycloak para redefinição de senha.

    Usa a required action ``UPDATE_PASSWORD`` via
    ``send_update_account``, que envia um e-mail com link assinado
    pelo próprio Keycloak — nenhum token de recuperação é gerado ou
    validado por este serviço.

    Args:
        login: RF, CPF ou username do usuário no Keycloak.

    Raises:
        KeycloakGetError: Se o usuário não existir no realm.
    """
    admin = obter_admin_keycloak()
    user_id = _resolver_user_id(admin, login)
    admin.send_update_account(
        user_id=user_id,
        payload=["UPDATE_PASSWORD"],
        client_id=settings.KEYCLOAK_LOGIN_CLIENT_ID,
    )


def disparar_verificacao_email(login: str) -> None:
    """Dispara o e-mail nativo do Keycloak para verificação de e-mail.

    Usa ``send_verify_email`` — o Keycloak envia o link de
    confirmação; este serviço não manipula o token de verificação.

    Args:
        login: RF, CPF ou username do usuário no Keycloak.

    Raises:
        KeycloakGetError: Se o usuário não existir no realm.
    """
    admin = obter_admin_keycloak()
    user_id = _resolver_user_id(admin, login)
    admin.send_verify_email(
        user_id=user_id,
        client_id=settings.KEYCLOAK_LOGIN_CLIENT_ID,
    )


def alterar_email(login: str, novo_email: str) -> dict[str, Any]:
    """Atualiza o e-mail do usuário e reabre a verificação.

    O Keycloak marca o novo e-mail como não verificado
    automaticamente ao atualizar o atributo; disparamos o envio do
    e-mail de verificação em seguida. As duas operações não são
    atômicas no Keycloak — se ``send_verify_email`` falhar depois de
    ``update_user`` já ter sido aplicado (ex.: instabilidade do
    servidor), o e-mail já mudou de fato. Por isso a falha na
    verificação é capturada separadamente em vez de propagar: quem
    chama precisa saber que a troca ocorreu mesmo que a notificação
    não tenha saído, em vez de receber um erro genérico que sugere
    que nada foi aplicado.

    Args:
        login: RF, CPF ou username do usuário no Keycloak.
        novo_email: Novo endereço de e-mail a ser associado.

    Returns:
        Dict com ``email_alterado`` (sempre ``True`` se não lançar) e
        ``verificacao_enviada`` (``False`` se ``send_verify_email``
        falhar após o e-mail já ter sido trocado).

    Raises:
        KeycloakGetError: Se o usuário não existir no realm.
        KeycloakError: Se a própria troca de e-mail (``update_user``)
            falhar — nesse caso nada foi aplicado.
    """
    admin = obter_admin_keycloak()
    user_id = _resolver_user_id(admin, login)
    admin.update_user(user_id=user_id, payload={"email": novo_email})

    try:
        admin.send_verify_email(
            user_id=user_id,
            client_id=settings.KEYCLOAK_LOGIN_CLIENT_ID,
        )
    except Exception:
        return {"email_alterado": True, "verificacao_enviada": False}

    return {"email_alterado": True, "verificacao_enviada": True}


def redefinir_senha(login: str, nova_senha: str) -> None:
    """Define uma nova senha definitiva para o usuário.

    Reset administrativo direto (ex.: suporte redefinindo a senha de
    um usuário). ``temporary=False`` define a senha como definitiva —
    diferente de ``UPDATE_PASSWORD`` via required action (usada em
    ``disparar_redefinicao_senha``), não força troca no próximo
    login, pois quem está definindo a senha aqui é uma ação
    administrativa explícita, não um esquecimento do usuário.

    Args:
        login: RF, CPF ou username do usuário no Keycloak.
        nova_senha: Nova senha a ser definida.

    Raises:
        KeycloakGetError: Se o usuário não existir no realm.
    """
    admin = obter_admin_keycloak()
    user_id = _resolver_user_id(admin, login)
    admin.set_user_password(
        user_id=user_id, password=nova_senha, temporary=False
    )


def buscar_usuario_por_login(admin: Any, login: str) -> dict[str, Any] | None:
    """Busca a conta do usuário por username, RF ou CPF.

    Mesma estratégia de busca do comando ``validar_login``: tenta
    username exato primeiro, depois os atributos customizados ``rf``
    e ``cpf`` (a plataforma usa RF/CPF como username na maioria dos
    casos, mas nem sempre).

    Args:
        admin: Cliente KeycloakAdmin autenticado.
        login: RF, CPF, e-mail ou username do usuário.

    Returns:
        Dados brutos da conta no Keycloak, ou ``None`` se não
        encontrada.
    """
    queries = [
        {"username": login, "exact": True},
        {"q": f"rf:{login}"},
        {"q": f"cpf:{login}"},
    ]
    if "@" in login:
        queries.append({"email": login, "exact": True})

    for query in queries:
        usuarios = admin.get_users(query=query)
        if usuarios:
            resultado: dict[str, Any] = usuarios[0]
            return resultado
    return None


def decodificar_claims_token(token: str) -> dict[str, Any]:
    """Decodifica o payload de um JWT sem validar a assinatura.

    Seguro neste contexto porque o token acabou de ser emitido pelo
    próprio Keycloak na mesma chamada (``kc_openid.token()``) — não é
    um token recebido de terceiros que precisaria de verificação.
    Usado tanto para extrair ``realm_access``/``resource_access``
    (roles) do access token quanto o ``sub`` (user id) do refresh
    token, quando não há outra forma de identificar o usuário na
    operação em questão (ex.: encerramento de sessão, que só recebe
    o refresh token).

    Args:
        token: JWT retornado por ``KeycloakOpenID.token()`` (access
            ou refresh token).

    Returns:
        Claims do token, ou ``{}`` se não for possível decodificar.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload))
        return claims
    except (IndexError, ValueError):
        return {}


def autenticar(login: str, senha: str) -> dict[str, Any]:
    """Autentica um usuário no Keycloak via OpenID Connect.

    Resolve o ``username`` real a partir do ``login`` informado (que
    pode ser RF, CPF, e-mail ou o próprio username) e efetua login
    via grant type ``password`` — mesmo fluxo do comando
    ``validar_login``, mas sem resetar senha: aqui a senha informada
    pelo usuário é usada como está.

    Args:
        login: RF, CPF, e-mail ou username do usuário.
        senha: Senha em texto plano.

    Returns:
        Dict com ``autenticado`` (bool) e, se sucesso, os dados da
        conta (``kc_user_id``, ``username``, ``nome``, ``email``,
        ``ativo``), ``roles`` (``realm_access``/``resource_access``
        extraídos do access token) e do token (``access_token``,
        ``refresh_token``, ``expires_in``); se falha, ``erro`` com o
        motivo.
    """
    from keycloak import KeycloakOpenID

    admin = obter_admin_keycloak()
    conta = buscar_usuario_por_login(admin, login)
    if not conta:
        return {"autenticado": False, "erro": ERRO_USUARIO_NAO_ENCONTRADO}

    kc_openid = KeycloakOpenID(
        server_url=settings.KEYCLOAK_URL_SERVIDOR,
        client_id=settings.KEYCLOAK_LOGIN_CLIENT_ID,
        client_secret_key=settings.KEYCLOAK_LOGIN_CLIENT_SECRET or None,
        realm_name=settings.KEYCLOAK_REALM,
        verify=settings.KEYCLOAK_VERIFICAR_SSL,
    )
    try:
        token = kc_openid.token(conta.get("username", login), senha)
    except Exception as exc:
        return {"autenticado": False, "erro": str(exc)}

    atributos = conta.get("attributes", {})
    nome = " ".join(
        filter(None, [conta.get("firstName"), conta.get("lastName")])
    )
    claims = decodificar_claims_token(token.get("access_token", ""))
    return {
        "autenticado": True,
        "kc_user_id": str(conta.get("id", "")),
        "username": conta.get("username", ""),
        "nome": nome,
        "email": conta.get("email"),
        "ativo": bool(conta.get("enabled")),
        "cpf": (atributos.get("cpf") or [None])[0],
        "rf": (atributos.get("rf") or [None])[0],
        "roles": {
            "realm_access": claims.get("realm_access", {}),
            "resource_access": claims.get("resource_access", {}),
        },
        "access_token": token.get("access_token", ""),
        "refresh_token": token.get("refresh_token", ""),
        "expires_in": token.get("expires_in"),
    }


def encerrar_sessao(refresh_token: str) -> dict[str, Any]:
    """Invalida a sessão associada ao refresh token informado.

    Equivale ao endpoint OIDC padrão do Keycloak
    (``/protocol/openid-connect/logout``), chamado com o mesmo client
    de login usado em ``autenticar`` — não um endpoint próprio deste
    serviço, o Keycloak é quem de fato encerra a sessão e emite o
    evento ``LOGOUT``.

    Args:
        refresh_token: Refresh token obtido no login, retornado por
            ``autenticar``.

    Returns:
        Dict com ``encerrada`` (``True`` se o Keycloak confirmou o
        encerramento; ``False`` se o token já estava inválido/
        expirado — não é considerado erro, o resultado prático já é
        o mesmo) e ``kc_user_id`` (extraído do próprio refresh token,
        usado para o gatilho de auditoria; ``None`` se não for
        possível decodificar).
    """
    from keycloak import KeycloakOpenID
    from keycloak.exceptions import KeycloakPostError

    kc_user_id = decodificar_claims_token(refresh_token).get("sub")

    kc_openid = KeycloakOpenID(
        server_url=settings.KEYCLOAK_URL_SERVIDOR,
        client_id=settings.KEYCLOAK_LOGIN_CLIENT_ID,
        client_secret_key=settings.KEYCLOAK_LOGIN_CLIENT_SECRET or None,
        realm_name=settings.KEYCLOAK_REALM,
        verify=settings.KEYCLOAK_VERIFICAR_SSL,
    )
    try:
        kc_openid.logout(refresh_token)
    except KeycloakPostError:
        return {"encerrada": False, "kc_user_id": kc_user_id}
    return {"encerrada": True, "kc_user_id": kc_user_id}


def obter_dados_usuario(login: str) -> dict[str, Any] | None:
    """Busca os dados cadastrais de um usuário no Keycloak.

    Não inclui ``roles``: montá-las aqui exigiria iterar todos os
    clients do realm via Admin API (~9 chamadas), pois este fluxo não
    tem um access token próprio do usuário para ler os claims direto
    do JWT (diferente de ``autenticar``). Testado e descartado por
    lentidão — Token Exchange (RFC 8693) também não está disponível
    nesta instância do Keycloak (``Standard token exchange is not
    enabled for the requested client``).

    Args:
        login: RF, CPF, e-mail ou username do usuário.

    Returns:
        Dict com ``kc_user_id``, ``username``, ``nome``, ``email``,
        ``ativo``, ``cpf`` e ``rf``, ou ``None`` se não encontrado.
    """
    admin = obter_admin_keycloak()
    conta = buscar_usuario_por_login(admin, login)
    if not conta:
        return None

    atributos = conta.get("attributes", {})
    nome = " ".join(
        filter(None, [conta.get("firstName"), conta.get("lastName")])
    )
    return {
        "kc_user_id": str(conta.get("id", "")),
        "username": conta.get("username", ""),
        "nome": nome,
        "email": conta.get("email"),
        "ativo": bool(conta.get("enabled")),
        "cpf": (atributos.get("cpf") or [None])[0],
        "rf": (atributos.get("rf") or [None])[0],
    }
