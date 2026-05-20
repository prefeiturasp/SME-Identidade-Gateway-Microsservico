import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def fake_token_response():
    from core.keycloak_client import TokenResponse

    return TokenResponse(
        access_token="ACCESS",
        refresh_token="REFRESH",
        id_token="ID",
        expires_in=300,
        refresh_expires_in=1800,
        token_type="Bearer",
        scope="openid profile",
        session_state="sess-123",
        raw={"access_token": "ACCESS"},
    )
