"""Composição do JWT enriquecido — auth-gateway-ms.

O Gateway *é* o auth-gateway-ms da arquitetura normativa da
plataforma SME-Identidade (``Memorias/projeto_referencia.md`` §2.6):
consome a identidade base do Keycloak e as projeções complementares
do SME-Identidade-Token-Microsservico (que não emite JWT — só
projeta claims, ver §3.6/§3.17) e compõe o token enriquecido.

Não é uma reassinatura do ``access_token`` do Keycloak — o Gateway
não tem a chave privada do Keycloak, então alterar aquele payload
invalidaria a assinatura RS256 original. É um JWT próprio, assinado
com uma chave do Gateway (``JWT_ENRIQUECIDO_SECRET``), usado para
compatibilidade com sistemas legados que esperam "um token" da
API/EOL — distinto do ``access_token`` OIDC, que continua disponível
para clientes que preferem validar direto contra o Keycloak.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from django.conf import settings

_ISSUER = "sme-identidade-gateway"


def compor_token_enriquecido(
    conta_keycloak: dict[str, Any],
    projecao_token_ms: dict[str, Any] | None,
    perfil: str | None = None,
) -> tuple[str, datetime]:
    """Monta e assina o JWT enriquecido a partir de Keycloak + Token-MS.

    A ausência de projeção no Token-MS (usuário autenticado no
    Keycloak mas sem registro complementar) não impede a composição
    — as claims de ``perfis``/``permissoes`` ficam vazias, refletindo
    o estado real, em vez de bloquear a emissão do token.

    Args:
        conta_keycloak: Conta já normalizada — mesmo formato de
            retorno de ``keycloak_admin.obter_dados_usuario``/
            ``keycloak_admin.autenticar`` (``kc_user_id``,
            ``username``, ``email``, ``rf``, ``cpf``), para não
            duplicar a lógica de extração de ``attributes`` brutos do
            Keycloak em mais de um lugar.
        projecao_token_ms: Corpo de
            ``GET /api/v1/perfis/{usuario_id}/`` do Token-MS, ou
            ``None`` se não houver projeção para o usuário.
        perfil: Perfil selecionado (rota
            ``usuarios/{login}/perfis/{perfil}/acesso/``). Ausente no
            login puro, onde nenhum perfil foi escolhido ainda.

    Returns:
        Tupla ``(token, data_expiracao)``.
    """
    agora = datetime.now(UTC)
    ttl = settings.JWT_ENRIQUECIDO_TTL_SEGUNDOS
    expiracao = agora + timedelta(seconds=ttl)

    claims: dict[str, Any] = {
        "iss": _ISSUER,
        "iat": int(agora.timestamp()),
        "exp": int(expiracao.timestamp()),
        "sub": str(conta_keycloak.get("kc_user_id", "")),
        "preferred_username": conta_keycloak.get("username", ""),
        "email": conta_keycloak.get("email"),
        "rf": conta_keycloak.get("rf"),
        "cpf": conta_keycloak.get("cpf"),
        "perfis": [],
        "permissoes": [],
    }

    if projecao_token_ms:
        claims.update(
            {
                "rf": projecao_token_ms.get("rf", claims["rf"]),
                "nome": projecao_token_ms.get("nome"),
                "cpf": projecao_token_ms.get("cpf", claims["cpf"]),
                "situacao": projecao_token_ms.get("situacao"),
                "dre_codigo": projecao_token_ms.get("dre_codigo"),
                "contrato_externo": projecao_token_ms.get(
                    "contrato_externo", False
                ),
                "perfis": projecao_token_ms.get("perfis", []),
                "permissoes": projecao_token_ms.get("permissoes", []),
            }
        )

    if perfil:
        claims["perfilSelecionado"] = perfil

    token = jwt.encode(
        claims,
        settings.JWT_ENRIQUECIDO_SECRET,
        algorithm=settings.JWT_ENRIQUECIDO_ALGORITMO,
    )
    return token, expiracao
