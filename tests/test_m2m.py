from unittest.mock import patch

import pytest

from core import keycloak_client


@pytest.fixture
def m2m_token():
    return keycloak_client.TokenResponse(
        access_token="M2M",
        refresh_token=None,
        id_token=None,
        expires_in=300,
        refresh_expires_in=None,
        token_type="Bearer",
        scope="sistema-x",
        session_state=None,
        raw={},
    )


@pytest.mark.django_db
def test_m2m_token_success_and_cache(api_client, m2m_token):
    with patch(
        "m2m.views.keycloak_client.client_credentials",
        return_value=m2m_token,
    ) as mock_call:
        first = api_client.post(
            "/api/v1/m2m/token/",
            {"client_id": "c", "client_secret": "s", "scope": "sistema-x"},
            format="json",
        )
        second = api_client.post(
            "/api/v1/m2m/token/",
            {"client_id": "c", "client_secret": "s", "scope": "sistema-x"},
            format="json",
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert mock_call.call_count == 1


@pytest.mark.django_db
def test_m2m_token_keycloak_error(api_client):
    err = keycloak_client.KeycloakError(
        "unauthorized_client", status_code=400, payload={"error": "unauthorized_client"}
    )
    with patch("m2m.views.keycloak_client.client_credentials", side_effect=err):
        resp = api_client.post(
            "/api/v1/m2m/token/",
            {"client_id": "c", "client_secret": "wrong"},
            format="json",
        )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_m2m_introspect(api_client):
    with patch(
        "m2m.views.keycloak_client.introspect",
        return_value={"active": True, "client_id": "c"},
    ):
        resp = api_client.post(
            "/api/v1/m2m/introspect/", {"token": "t"}, format="json"
        )
    assert resp.status_code == 200
    assert resp.json()["active"] is True


@pytest.mark.django_db
def test_m2m_introspect_error(api_client):
    err = keycloak_client.KeycloakError("bad", status_code=400, payload={})
    with patch("m2m.views.keycloak_client.introspect", side_effect=err):
        resp = api_client.post(
            "/api/v1/m2m/introspect/", {"token": "t"}, format="json"
        )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_m2m_token_validation(api_client):
    resp = api_client.post("/api/v1/m2m/token/", {}, format="json")
    assert resp.status_code == 400
