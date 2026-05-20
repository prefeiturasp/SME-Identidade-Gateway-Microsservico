"""Compat endpoints that emulate the .NET API EOL surface.

These endpoints exist *only* to keep legacy systems alive while they migrate
to OIDC. The flow:

1. Cliente legado faz POST ``/api/v1/autenticacao`` com ``login``/``senha``.
2. Gateway autentica contra o Keycloak (password grant interno).
3. Caso o usuário não tenha enriquecimento ainda, o gateway pode consultar o
   token-ms para hidratar o claim ``permissoes``.
4. Devolve o body no mesmo shape esperado pelos sistemas .NET — incluindo o
   campo ``status`` (enum ``RetornoCoreSSO``) e o JWT legado.

A documentação completa do shape está em ``Docs/imagem.png``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core import audit, keycloak_client, token_ms_client

from .jwt_compat import encode_legacy_token
from .serializers import LoginRequestSerializer, TokenDataRequestSerializer

logger = logging.getLogger(__name__)


# Enum RetornoCoreSSO (ver imagem do fluxo).
STATUS_OK = 0
STATUS_SENHA_PADRAO = 1
STATUS_SENHA_ERRADA = 2
STATUS_SEM_SENHA_PADRAO = 3
STATUS_NAO_ENCONTRADO = 4


def _map_keycloak_error_to_status(exc: keycloak_client.KeycloakError) -> int:
    description = (exc.payload or {}).get("error_description", "").lower()
    if "user not found" in description or "no user" in description:
        return STATUS_NAO_ENCONTRADO
    if "invalid user credentials" in description or "invalid_grant" in description:
        return STATUS_SENHA_ERRADA
    if exc.status_code == 401:
        return STATUS_SENHA_ERRADA
    return STATUS_NAO_ENCONTRADO


@api_view(["POST"])
@permission_classes([AllowAny])
def autenticacao(request):
    """POST /api/v1/autenticacao — primeira consulta do fluxo legado."""
    serializer = LoginRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    v = serializer.validated_data

    try:
        tok = keycloak_client.password_grant(v["login"], v["senha"])
    except keycloak_client.KeycloakError as exc:
        mapped = _map_keycloak_error_to_status(exc)
        audit.publish(
            "legacy.autenticacao.failure",
            {"login": v["login"], "status": mapped, "reason": str(exc)},
        )
        return Response(
            {
                "status": mapped,
                "usuarioId": None,
                "nome": None,
                "codigoRf": None,
            },
            status=status.HTTP_200_OK
            if mapped == STATUS_NAO_ENCONTRADO
            else status.HTTP_401_UNAUTHORIZED,
        )

    claims = token_ms_client.fetch_claims(v["login"])
    audit.publish(
        "legacy.autenticacao.success",
        {"login": v["login"], "session_state": tok.session_state},
    )
    body = {
        "status": STATUS_OK,
        "usuarioId": claims.get("usuarioId"),
        "nome": claims.get("nome"),
        "codigoRf": claims.get("codigoRf"),
        "accessToken": tok.access_token,
        "refreshToken": tok.refresh_token,
        "expiresIn": tok.expires_in,
    }
    return Response(body)


@api_view(["GET"])
@permission_classes([AllowAny])
def carregar_perfis(_request, login: str):
    """GET /api/v1/autenticacaoSgp/CarregarPerfisPorLogin/{login} — segunda consulta."""
    claims = token_ms_client.fetch_claims(login)
    body = {
        "codigoRf": claims.get("codigoRf"),
        "perfis": claims.get("perfis", []),
        "possuiCargoCJ": bool(claims.get("possuiCargoCJ", False)),
        "possuiPerfilCJ": bool(claims.get("possuiPerfilCJ", False)),
        "contratoExterno": bool(claims.get("contratoExterno", False)),
    }
    return Response(body)


@api_view(["GET"])
@permission_classes([AllowAny])
def dados_usuario(_request, login: str):
    """GET /api/v1/autenticacaoSgp/{login}/dados — terceira consulta."""
    claims = token_ms_client.fetch_claims(login)
    body = {
        "cpf": claims.get("cpf"),
        "nome": claims.get("nome"),
        "codigoRf": claims.get("codigoRf"),
        "email": claims.get("email"),
        "dreCodigo": claims.get("dreCodigo"),
        "emailValido": bool(claims.get("emailValido", False)),
    }
    return Response(body)


@api_view(["GET"])
@permission_classes([AllowAny])
def carregar_dados_acesso(_request, usuario_id: str, perfil_id: str):
    """GET /api/v1/autenticacaoSgp/CarregarDadosAcesso/usuarios/{0}/perfis/{1}.

    Emite o JWT legado embutindo permissões resolvidas pelo token-ms.
    """
    enrichment = token_ms_client.fetch_claims(usuario_id) or {}
    permissoes = enrichment.get("permissoes_por_perfil", {}).get(str(perfil_id), [])

    token, ttl = encode_legacy_token(
        {
            "sub": usuario_id,
            "perfil": perfil_id,
            "permissoes": permissoes,
        }
    )
    expiracao = datetime.now(timezone.utc).timestamp() + ttl

    audit.publish(
        "legacy.dados_acesso",
        {"usuario_id": usuario_id, "perfil_id": perfil_id, "permissoes": len(permissoes)},
    )

    return Response(
        {
            "token": token,
            "dataHoraExpiracao": datetime.fromtimestamp(
                expiracao, tz=timezone.utc
            ).isoformat(),
            "permissoes": permissoes,
        }
    )
