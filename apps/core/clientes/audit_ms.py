"""Cliente HTTP para o SME-Identidade-Audit-Microsservico.

Um cliente ``httpx`` de módulo, configurado com URL base, timeout e
uma API Key própria (``API_KEY_AUDIT_MS``), independente da API Key
que autentica requisições recebidas pelo Gateway.

O timeout padrão é curto de propósito: quem usa este cliente dispara
um gatilho acessório em paralelo a uma resposta que já está pronta
para ser entregue — um destino lento não pode segurar essa resposta.
"""

from __future__ import annotations

import httpx
from django.conf import settings


def cliente_audit_ms() -> httpx.Client:
    """Cliente HTTP reutilizável para o SME-Identidade-Audit-Microsservico.

    Returns:
        Cliente ``httpx`` configurado com a URL base, timeout e o
        header de API Key esperados pelo Audit-MS.
    """
    header = settings.API_KEY_AUDIT_MS_HEADER
    return httpx.Client(
        base_url=settings.AUDIT_MS_URL,
        timeout=settings.AUDIT_MS_TIMEOUT,
        headers={header: settings.API_KEY_AUDIT_MS},
    )
