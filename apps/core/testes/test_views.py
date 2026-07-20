"""Testes da views do módulo core."""

from unittest.mock import MagicMock, patch

import httpx
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

_CLIENTE_TOKEN_MS = "apps.core.api.views.cliente_token_ms"


def _mock_cliente(resposta: httpx.Response) -> MagicMock:
    """Monta um MagicMock de cliente_token_ms() usável como context manager."""
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.get.return_value = resposta
    return cliente


class TestHealthCheckView:
    """Testes da view HealthCheckView."""

    def test_deve_retornar_healthy_quando_token_ms_saudavel(self) -> None:
        """Deve reportar token_ms healthy quando ele responder 200."""
        resposta_token_ms = httpx.Response(
            200,
            json={"status": "healthy"},
            request=httpx.Request("GET", "http://token-ms/api/v1/health/"),
        )
        cliente = _mock_cliente(resposta_token_ms)
        with patch(_CLIENTE_TOKEN_MS, return_value=cliente):
            response = APIClient().get(reverse("health-check"))

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "healthy",
            "dependencias": {"token_ms": "healthy"},
        }
        args, _ = cliente.get.call_args
        assert args[0] == "/api/v1/health/"

    def test_deve_retornar_degraded_quando_token_ms_responde_erro(
        self,
    ) -> None:
        """Deve reportar token_ms degraded se ele não responder 200."""
        resposta_token_ms = httpx.Response(
            500,
            json={"detalhe": "erro"},
            request=httpx.Request("GET", "http://token-ms/health/"),
        )
        with patch(
            _CLIENTE_TOKEN_MS, return_value=_mock_cliente(resposta_token_ms)
        ):
            response = APIClient().get(reverse("health-check"))

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert corpo["status"] == "healthy"
        assert corpo["dependencias"]["token_ms"] == "degraded"

    def test_deve_retornar_unhealthy_quando_token_ms_inacessivel(
        self,
    ) -> None:
        """Deve reportar token_ms unhealthy sem derrubar o próprio Gateway."""
        cliente = MagicMock()
        cliente.__enter__.return_value = cliente
        cliente.get.side_effect = httpx.ConnectError("recusado")

        with patch(_CLIENTE_TOKEN_MS, return_value=cliente):
            response = APIClient().get(reverse("health-check"))

        assert response.status_code == status.HTTP_200_OK
        corpo = response.json()
        assert corpo["status"] == "healthy"
        assert corpo["dependencias"]["token_ms"] == "unhealthy"
