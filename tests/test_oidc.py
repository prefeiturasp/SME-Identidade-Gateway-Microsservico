from unittest.mock import patch

import pytest

from core import keycloak_client


@pytest.mark.django_db
def test_oidc_token_success(api_client, fake_token_response):
    with patch("auth_oidc.views.keycloak_client.password_grant",
               return_value=fake_token_response) as mock_grant, \
         patch("auth_oidc.views.token_ms_client.fetch_claims",
               return_value={"nome": "Maria"}) as mock_claims:
        resp = api_client.post(
            "/api/v1/oidc/token/",
            {"username": "12345678901", "password": "x"},
            format="json",
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "ACCESS"
    assert body["claims"] == {"nome": "Maria"}
    mock_grant.assert_called_once()
    mock_claims.assert_called_once_with("12345678901")


@pytest.mark.django_db
def test_oidc_token_invalid_credentials(api_client):
    err = keycloak_client.KeycloakError(
        "invalid_grant",
        status_code=401,
        payload={"error": "invalid_grant", "error_description": "Invalid user credentials"},
    )
    with patch("auth_oidc.views.keycloak_client.password_grant", side_effect=err):
        resp = api_client.post(
            "/api/v1/oidc/token/",
            {"username": "x", "password": "y"},
            format="json",
        )
    assert resp.status_code == 401
    assert "invalid_grant" in resp.json()["detail"]


@pytest.mark.django_db
def test_oidc_refresh_passthrough(api_client, fake_token_response):
    with patch("auth_oidc.views.keycloak_client.refresh_token",
               return_value=fake_token_response):
        resp = api_client.post(
            "/api/v1/oidc/refresh/",
            {"refresh_token": "abc"},
            format="json",
        )
    assert resp.status_code == 200
    # Refresh não enriquece com claims.
    assert "claims" not in resp.json()


@pytest.mark.django_db
def test_oidc_introspect(api_client):
    with patch(
        "auth_oidc.views.keycloak_client.introspect",
        return_value={"active": True, "sub": "abc"},
    ):
        resp = api_client.post(
            "/api/v1/oidc/introspect/", {"token": "tok"}, format="json"
        )
    assert resp.status_code == 200
    assert resp.json()["active"] is True


@pytest.mark.django_db
def test_oidc_logout(api_client):
    with patch("auth_oidc.views.keycloak_client.logout") as mock_logout:
        resp = api_client.post(
            "/api/v1/oidc/logout/", {"refresh_token": "abc"}, format="json"
        )
    assert resp.status_code == 200
    mock_logout.assert_called_once()


@pytest.mark.django_db
def test_oidc_logout_error(api_client):
    err = keycloak_client.KeycloakError("boom", status_code=502, payload={})
    with patch("auth_oidc.views.keycloak_client.logout", side_effect=err):
        resp = api_client.post(
            "/api/v1/oidc/logout/", {"refresh_token": "abc"}, format="json"
        )
    assert resp.status_code == 502


@pytest.mark.django_db
def test_oidc_discovery_and_jwks(api_client):
    with patch(
        "auth_oidc.views.keycloak_client.well_known",
        return_value={"issuer": "kc"},
    ), patch(
        "auth_oidc.views.keycloak_client.jwks",
        return_value={"keys": []},
    ):
        wn = api_client.get("/api/v1/oidc/.well-known/openid-configuration")
        jw = api_client.get("/api/v1/oidc/certs/")
    assert wn.status_code == 200
    assert wn.json()["issuer"] == "kc"
    assert jw.status_code == 200
    assert "keys" in jw.json()


@pytest.mark.django_db
def test_oidc_discovery_error(api_client):
    err = keycloak_client.KeycloakError("down", status_code=503, payload={})
    with patch("auth_oidc.views.keycloak_client.well_known", side_effect=err):
        resp = api_client.get("/api/v1/oidc/.well-known/openid-configuration")
    assert resp.status_code == 503


@pytest.mark.django_db
def test_oidc_token_validation_error(api_client):
    resp = api_client.post("/api/v1/oidc/token/", {}, format="json")
    assert resp.status_code == 400
