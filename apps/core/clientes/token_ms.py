"""Cliente HTTP para o SME-Identidade-Token-Microsservico.

Mesmo padrão de ``apps.gestao_usuario.cliente_etl``: um cliente
``httpx`` de módulo, configurado com a URL base, timeout e a API Key
de serviço a serviço própria do Token-MS (``API_KEY_TOKEN_MS``),
distinta da API Key que os clientes externos usam para chamar o
Gateway.
"""

from __future__ import annotations

import httpx
from django.conf import settings


def cliente_token_ms() -> httpx.Client:
    """Cliente HTTP reutilizável para o SME-Identidade-Token-Microsservico.

    Returns:
        Cliente ``httpx`` configurado com a URL base, timeout e o
        header de API Key esperados pelo Token-MS.
    """
    header = settings.API_KEY_TOKEN_MS_HEADER
    return httpx.Client(
        base_url=settings.TOKEN_MS_URL,
        timeout=settings.TOKEN_MS_TIMEOUT,
        headers={header: settings.API_KEY_TOKEN_MS},
    )
