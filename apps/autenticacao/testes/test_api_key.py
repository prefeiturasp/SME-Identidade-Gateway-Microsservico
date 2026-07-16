"""Testes da autenticação por API Key."""

import pytest
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.autenticacao.api_key import AutenticacaoApiKey


class TestAutenticacaoApiKey:
    """Testes da classe AutenticacaoApiKey."""

    def setup_method(self) -> None:
        """Prepara a fábrica de requisições e a instância testada."""
        self.factory = APIRequestFactory()
        self.autenticacao = AutenticacaoApiKey()

    @override_settings(API_KEY="chave-secreta", API_KEY_HEADER="X-API-Key")
    def test_deve_autenticar_com_chave_valida(self) -> None:
        """Deve autenticar quando a chave enviada é a esperada."""
        request = self.factory.get("/", HTTP_X_API_KEY="chave-secreta")

        resultado = self.autenticacao.authenticate(request)

        assert resultado is not None
        usuario, credenciais = resultado
        assert usuario.is_authenticated is True
        assert credenciais is None

    @override_settings(API_KEY="chave-secreta", API_KEY_HEADER="X-API-Key")
    def test_deve_rejeitar_chave_invalida(self) -> None:
        """Deve rejeitar quando a chave enviada não confere."""
        request = self.factory.get("/", HTTP_X_API_KEY="chave-errada")

        with pytest.raises(AuthenticationFailed):
            self.autenticacao.authenticate(request)

    @override_settings(API_KEY="chave-secreta", API_KEY_HEADER="X-API-Key")
    def test_deve_retornar_none_sem_header(self) -> None:
        """Deve retornar None quando o header não é enviado."""
        request = self.factory.get("/")

        resultado = self.autenticacao.authenticate(request)

        assert resultado is None
