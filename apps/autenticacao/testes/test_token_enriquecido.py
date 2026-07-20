"""Testes da composição do JWT enriquecido."""

from datetime import UTC, datetime
from typing import Any

import jwt
import pytest

from apps.autenticacao.token_enriquecido import compor_token_enriquecido

_CONTA_KEYCLOAK = {
    "kc_user_id": "5c29cc47-...",
    "username": "1234567",
    "nome": "FULANO DE TAL",
    "email": "fulano@sme.sp.gov.br",
    "ativo": True,
    "cpf": "12345678900",
    "rf": "1234567",
}

_PROJECAO_TOKEN_MS = {
    "rf": "1234567",
    "nome": "FULANO DE TAL",
    "cpf": "12345678900",
    "situacao": "ativo",
    "dre_codigo": "108000",
    "contrato_externo": False,
    "perfis": [{"id": "b2b2b2b2-...", "nome": "professor", "ativo": True}],
    "permissoes": [
        {
            "sistema_id": 1,
            "sistema_nome": "CoreSSO",
            "modulo_id": 3,
            "modulo_nome": "Usuários",
            "consultar": True,
            "inserir": False,
            "alterar": False,
            "excluir": False,
        }
    ],
}


@pytest.fixture(autouse=True)
def _configura_secret(settings: Any) -> None:
    """Define o secret/algoritmo/TTL do token enriquecido para os testes."""
    settings.JWT_ENRIQUECIDO_SECRET = "secret-de-teste"
    settings.JWT_ENRIQUECIDO_ALGORITMO = "HS256"
    settings.JWT_ENRIQUECIDO_TTL_SEGUNDOS = 28800


class TestComporTokenEnriquecido:
    """Testes de ``compor_token_enriquecido``."""

    def test_inclui_claims_do_keycloak_e_do_token_ms(self) -> None:
        """Deve incluir claims de ambas as fontes."""
        token, _ = compor_token_enriquecido(
            _CONTA_KEYCLOAK, _PROJECAO_TOKEN_MS, perfil="professor"
        )

        claims = jwt.decode(token, "secret-de-teste", algorithms=["HS256"])
        assert claims["sub"] == "5c29cc47-..."
        assert claims["preferred_username"] == "1234567"
        assert claims["email"] == "fulano@sme.sp.gov.br"
        assert claims["rf"] == "1234567"
        assert claims["dre_codigo"] == "108000"
        assert claims["contrato_externo"] is False
        assert claims["perfis"][0]["nome"] == "professor"
        assert claims["permissoes"][0]["sistema_nome"] == "CoreSSO"
        assert claims["perfilSelecionado"] == "professor"
        assert claims["iss"] == "sme-identidade-gateway"

    def test_sem_projecao_token_ms_claims_complementares_ficam_vazias(
        self,
    ) -> None:
        """Não deve bloquear a composição quando não há projeção."""
        token, _ = compor_token_enriquecido(_CONTA_KEYCLOAK, None)

        claims = jwt.decode(token, "secret-de-teste", algorithms=["HS256"])
        assert claims["sub"] == "5c29cc47-..."
        assert claims["rf"] == "1234567"
        assert claims["perfis"] == []
        assert claims["permissoes"] == []
        assert "perfilSelecionado" not in claims

    def test_sem_perfil_nao_inclui_perfil_selecionado(self) -> None:
        """``perfilSelecionado`` só existe quando ``perfil`` é informado."""
        token, _ = compor_token_enriquecido(
            _CONTA_KEYCLOAK, _PROJECAO_TOKEN_MS
        )

        claims = jwt.decode(token, "secret-de-teste", algorithms=["HS256"])
        assert "perfilSelecionado" not in claims

    def test_expiracao_reflete_o_ttl_configurado(self, settings: Any) -> None:
        """``exp`` deve refletir ``JWT_ENRIQUECIDO_TTL_SEGUNDOS``."""
        settings.JWT_ENRIQUECIDO_TTL_SEGUNDOS = 60

        antes = datetime.now(UTC)
        token, expiracao = compor_token_enriquecido(_CONTA_KEYCLOAK, None)

        claims = jwt.decode(token, "secret-de-teste", algorithms=["HS256"])
        delta = claims["exp"] - claims["iat"]
        assert delta == 60
        assert 59 <= (expiracao - antes).total_seconds() <= 61

    def test_token_nao_decodifica_com_secret_errado(self) -> None:
        """Deve estar assinado — outro secret não decodifica o token."""
        token, _ = compor_token_enriquecido(_CONTA_KEYCLOAK, None)

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "secret-errado", algorithms=["HS256"])
