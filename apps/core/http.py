"""Utilitário compartilhado para repassar respostas de serviços HTTP.

Usado pelas views que proxeiam chamadas a outros microsserviços da
plataforma (ETL, Token-MS) — extraído de
``apps.gestao_usuario.api.views`` para não duplicar o tratamento de
corpo vazio e de resposta não-JSON entre os dois clientes.
"""

from __future__ import annotations

import httpx
from rest_framework.response import Response


def resposta_do_servico(resposta: httpx.Response) -> Response:
    """Monta a ``Response`` a partir da resposta de um serviço interno.

    O serviço de origem pode ficar atrás de proxies/WAF que respondem
    com uma página de erro HTML (ex.: 404 de infraestrutura) em vez
    do JSON esperado — nesse caso ``resposta.json()`` lançaria
    ``JSONDecodeError`` sem ser capturado, derrubando a view com 500
    em vez de repassar um erro tratável ao cliente.

    Args:
        resposta: Resposta HTTP recebida do serviço interno.

    Returns:
        ``Response`` do DRF com o mesmo status, e corpo JSON quando
        houver; ``502`` com detalhe se o corpo não for JSON válido.
    """
    if not resposta.content:
        return Response(None, status=resposta.status_code)
    try:
        return Response(resposta.json(), status=resposta.status_code)
    except ValueError:
        return Response(
            {
                "erro": "resposta inválida do serviço",
                "status_servico": resposta.status_code,
            },
            status=502,
        )
