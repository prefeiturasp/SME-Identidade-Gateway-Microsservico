"""Disparo do gatilho de auditoria a partir dos fluxos de credencial.

O que sai daqui não é um evento de auditoria: é só um aviso de que
determinado usuário teve atividade agora, para que a captura consulte
o Keycloak antes do próximo ciclo agendado. O evento em si é sempre
lido do Keycloak, nunca montado aqui — dois produtores de evento
gerariam dois timestamps diferentes para a mesma atividade, e a
deduplicação no destino teria de reconciliar formatos divergentes.

O disparo é acessório ao fluxo que o usuário está esperando: falha de
rede, timeout ou destino fora do ar são engolidos de propósito, no
mesmo padrão de degradação graciosa já usado quando o token
enriquecido não pode ser obtido.
"""

from __future__ import annotations

import httpx
from django.conf import settings

from apps.autenticacao import keycloak_admin
from apps.core.api_clients import get_api_client

_ROTA_GATILHO = "/api/v1/gatilho-poll/"

_client = get_api_client("auditoria")


def disparar_gatilho(realm: str, usuario_id: str | None) -> bool:
    """Avisa o serviço de auditoria que houve atividade de um usuário.

    Args:
        realm: Realm do Keycloak onde a atividade aconteceu.
        usuario_id: Identificador do usuário no Keycloak
            (``kc_user_id``), quando conhecido.

    Returns:
        ``True`` se o aviso foi aceito pelo destino, ``False`` em
        qualquer outro caso — inclusive falha de comunicação, que
        nunca é propagada ao chamador.
    """
    if not usuario_id:
        return False

    try:
        resposta = _client.post(
            _ROTA_GATILHO,
            payload={"realm": realm, "usuario_id": usuario_id},
        )
    except httpx.HTTPError:
        return False

    return resposta.status_code == 202


def disparar_gatilho_por_login(login: str) -> bool:
    """Avisa o serviço de auditoria a partir do login do usuário.

    As rotas de credencial recebem RF, CPF ou e-mail, enquanto o aviso
    trafega o identificador do usuário no Keycloak — daí a resolução
    da conta antes do envio. Assim como o próprio envio, a resolução
    é acessória: se o Keycloak não responder, o aviso simplesmente
    não sai e a operação de credencial, que já foi concluída, segue
    intacta. O mesmo vale quando o login informado é o e-mail que
    acabou de ser substituído — a busca não o encontra mais, e o
    ciclo agendado captura o evento pelo caminho normal.

    Args:
        login: RF, CPF, e-mail ou username do usuário.

    Returns:
        ``True`` se o aviso foi aceito pelo destino, ``False`` em
        qualquer outro caso.
    """
    try:
        conta = keycloak_admin.obter_dados_usuario(login)
    except Exception:
        return False

    if not conta:
        return False

    return disparar_gatilho(
        settings.KEYCLOAK_REALM,
        conta.get("kc_user_id"),
    )
