"""Testes da views do módulo core."""

from unittest.mock import MagicMock, patch

import httpx
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

_TOKEN_MS_CLIENT = "apps.core.api.views._client"


def _mock_cliente(
    resposta: httpx.Response,
) -> MagicMock:
    """Monta um mock do cliente HTTP do Token-MS."""
    cliente = MagicMock()
    cliente.get.return_value = resposta
    return cliente


class TestHealthCheckView:
    """Testes da view HealthCheckView."""

    def test_deve_retornar_healthy_quando_token_ms_saudavel(
        self,
    ) -> None:
        """Deve reportar token_ms healthy quando ele responder 200."""
        resposta_token_ms = httpx.Response(
            status.HTTP_200_OK,
            json={"status": "healthy"},
            request=httpx.Request(
                "GET",
                "http://token-ms/api/v1/health/",
            ),
        )

        cliente = _mock_cliente(resposta_token_ms)

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().get(reverse("health-check"))

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "healthy",
            "dependencias": {
                "token_ms": "healthy",
            },
        }

        cliente.get.assert_called_once_with("/api/v1/health/")

    def test_deve_retornar_degraded_quando_token_ms_responde_erro(
        self,
    ) -> None:
        """Deve reportar token_ms degraded se ele não responder 200."""
        resposta_token_ms = httpx.Response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            json={"detalhe": "erro"},
            request=httpx.Request(
                "GET",
                "http://token-ms/api/v1/health/",
            ),
        )

        cliente = _mock_cliente(resposta_token_ms)

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().get(reverse("health-check"))

        assert response.status_code == status.HTTP_200_OK

        corpo = response.json()

        assert corpo["status"] == "healthy"
        assert corpo["dependencias"]["token_ms"] == "degraded"

        cliente.get.assert_called_once_with("/api/v1/health/")

    def test_deve_retornar_unhealthy_quando_token_ms_inacessivel(
        self,
    ) -> None:
        """Deve reportar token_ms unhealthy sem derrubar o próprio Gateway."""
        cliente = MagicMock()
        cliente.get.side_effect = httpx.ConnectError("recusado")

        with patch(_TOKEN_MS_CLIENT, cliente):
            response = APIClient().get(reverse("health-check"))

        assert response.status_code == status.HTTP_200_OK

        corpo = response.json()

        assert corpo["status"] == "healthy"
        assert corpo["dependencias"]["token_ms"] == "unhealthy"

        cliente.get.assert_called_once_with("/api/v1/health/")
