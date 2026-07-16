"""Cliente HTTP para o SME-Identidade-ETL.

O Gateway não fala com o Keycloak Admin API para provisionamento de
identidade — essa responsabilidade é do ETL (única lógica real de
upsert, hash, idempotência e roles). As rotas de gestão de usuário
do Gateway apenas autenticam a requisição do cliente externo, validam
o payload de entrada e repassam para o ETL via HTTP, usando uma API
Key de serviço a serviço própria (``API_KEY_ETL``), distinta da API
Key que os clientes usam para chamar o Gateway.
"""

from __future__ import annotations

import httpx
from django.conf import settings


def cliente_etl() -> httpx.Client:
    """Cliente HTTP reutilizável para o SME-Identidade-ETL.

    Returns:
        Cliente ``httpx`` configurado com a URL base, timeout e o
        header de API Key esperados pelo ETL.
    """
    header = settings.API_KEY_ETL_HEADER
    return httpx.Client(
        base_url=settings.ETL_URL,
        timeout=settings.ETL_TIMEOUT,
        headers={header: settings.API_KEY_ETL},
    )
