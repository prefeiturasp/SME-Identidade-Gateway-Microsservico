"""Views da API da aplicação core."""

from __future__ import annotations

import httpx
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import HealthStatusSerializer
from apps.core.clientes.token_ms import cliente_token_ms


class HealthCheckView(APIView):
    """Disponibiliza o endpoint de verificação de saúde da aplicação."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """Retorna o estado de saúde da aplicação e de suas dependências.

        O status do Token-MS é informativo — nunca torna o próprio
        Gateway "unhealthy" (um health check que falha porque uma
        dependência caiu é um anti-padrão clássico, derruba
        orquestradores/load balancers desnecessariamente).

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Resposta HTTP contendo o status da aplicação e o estado
            observado do Token-MS em ``dependencias.token_ms``.
        """
        situacao_token_ms = "healthy"
        try:
            with cliente_token_ms() as cliente:
                resposta = cliente.get("/api/v1/health/", timeout=2)
                if resposta.status_code != 200:
                    situacao_token_ms = "degraded"
        except httpx.HTTPError:
            situacao_token_ms = "unhealthy"

        serializer = HealthStatusSerializer(
            {
                "status": "healthy",
                "dependencias": {"token_ms": situacao_token_ms},
            },
        )

        return Response(serializer.data)
