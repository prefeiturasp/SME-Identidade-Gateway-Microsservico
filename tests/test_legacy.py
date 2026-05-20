from unittest.mock import patch

import jwt
import pytest
from django.conf import settings

from auth_legacy.jwt_compat import decode_legacy_token, encode_legacy_token
from core import keycloak_client


@pytest.mark.django_db
def test_legacy_autenticacao_success(api_client, fake_token_response):
    with patch(
        "auth_legacy.views.keycloak_client.password_grant",
        return_value=fake_token_response,
    ), patch(
        "auth_legacy.views.token_ms_client.fetch_claims",
        return_value={"usuarioId": "u1", "nome": "Joana", "codigoRf": "12345"},
    ):
        resp = api_client.post(
            "/api/v1/autenticacao",
            {"login": "12345", "senha": "secret"},
            format="json",
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == 0
    assert body["nome"] == "Joana"
    assert body["accessToken"] == "ACCESS"


@pytest.mark.django_db
def test_legacy_autenticacao_user_not_found(api_client):
    err = keycloak_client.KeycloakError(
        "invalid_grant",
        status_code=401,
        payload={"error": "invalid_grant", "error_description": "User not found"},
    )
    with patch("auth_legacy.views.keycloak_client.password_grant", side_effect=err):
        resp = api_client.post(
            "/api/v1/autenticacao",
            {"login": "00000000000", "senha": "x"},
            format="json",
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == 4


@pytest.mark.django_db
def test_legacy_autenticacao_wrong_password(api_client):
    err = keycloak_client.KeycloakError(
        "invalid_grant",
        status_code=401,
        payload={
            "error": "invalid_grant",
            "error_description": "Invalid user credentials",
        },
    )
    with patch("auth_legacy.views.keycloak_client.password_grant", side_effect=err):
        resp = api_client.post(
            "/api/v1/autenticacao",
            {"login": "12345", "senha": "wrong"},
            format="json",
        )
    assert resp.status_code == 401
    assert resp.json()["status"] == 2


@pytest.mark.django_db
def test_legacy_carregar_perfis(api_client):
    with patch(
        "auth_legacy.views.token_ms_client.fetch_claims",
        return_value={
            "codigoRf": "12345",
            "perfis": ["uuid-1"],
            "possuiCargoCJ": True,
        },
    ):
        resp = api_client.get(
            "/api/v1/autenticacaoSgp/CarregarPerfisPorLogin/12345"
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["codigoRf"] == "12345"
    assert body["possuiCargoCJ"] is True
    assert body["perfis"] == ["uuid-1"]


@pytest.mark.django_db
def test_legacy_dados_usuario(api_client):
    with patch(
        "auth_legacy.views.token_ms_client.fetch_claims",
        return_value={"cpf": "111", "nome": "Z", "email": "a@b"},
    ):
        resp = api_client.get("/api/v1/autenticacaoSgp/12345/dados")
    assert resp.status_code == 200
    assert resp.json()["cpf"] == "111"


@pytest.mark.django_db
def test_legacy_carregar_dados_acesso(api_client):
    with patch(
        "auth_legacy.views.token_ms_client.fetch_claims",
        return_value={"permissoes_por_perfil": {"p-1": ["READ", "WRITE"]}},
    ):
        resp = api_client.get(
            "/api/v1/autenticacaoSgp/CarregarDadosAcesso/usuarios/u-1/perfis/p-1"
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["permissoes"] == ["READ", "WRITE"]
    payload = decode_legacy_token(body["token"])
    assert payload["sub"] == "u-1"
    assert payload["permissoes"] == ["READ", "WRITE"]


def test_jwt_compat_roundtrip():
    token, ttl = encode_legacy_token({"sub": "abc"})
    decoded = jwt.decode(
        token,
        settings.LEGACY_JWT_SECRET,
        algorithms=["HS256"],
        issuer=settings.LEGACY_JWT_ISSUER,
    )
    assert decoded["sub"] == "abc"
    assert ttl == settings.LEGACY_JWT_TTL
