"""Testes do utilitário compartilhado de respostas HTTP."""

import httpx
from rest_framework import status

from apps.core.http import resposta_do_servico


def test_resposta_do_servico_com_corpo_vazio() -> None:
    """Deve preservar o status quando o serviço retornar corpo vazio."""
    resposta = httpx.Response(
        status.HTTP_204_NO_CONTENT,
        content=b"",
        request=httpx.Request("GET", "https://servico/teste"),
    )

    response = resposta_do_servico(resposta)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.data is None
