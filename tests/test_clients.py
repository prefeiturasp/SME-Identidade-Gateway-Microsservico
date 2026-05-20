"""Tests for the low-level keycloak HTTP client and token-ms client."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from core import audit, keycloak_client, token_ms_client


def _fake_response(status_code=200, json_body=None, *, content=b"{}"):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = content
    resp.json.return_value = json_body if json_body is not None else {}
    resp.text = "" if json_body is None else "body"
    return resp


def _client_ctx(response):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.return_value = response
    client.get.return_value = response
    return client


@pytest.fixture
def kc_token_payload():
    return {
        "access_token": "AA",
        "refresh_token": "RR",
        "id_token": "II",
        "expires_in": 300,
        "refresh_expires_in": 1800,
        "token_type": "Bearer",
        "scope": "openid",
        "session_state": "s",
    }


def test_password_grant_parses_token(kc_token_payload):
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(
            _fake_response(200, kc_token_payload, content=b"{}")
        )
        tok = keycloak_client.password_grant("u", "p")
    assert tok.access_token == "AA"
    assert tok.expires_in == 300


def test_password_grant_includes_secret(kc_token_payload):
    captured = {}

    def _post(url, data, headers):
        captured["data"] = data
        return _fake_response(200, kc_token_payload)

    with patch("core.keycloak_client.httpx.Client") as MockClient:
        client = _client_ctx(_fake_response(200, kc_token_payload))
        client.post.side_effect = _post
        MockClient.return_value = client
        keycloak_client.password_grant(
            "u", "p", client_id="x", client_secret="sekret", scope="openid email"
        )
    assert captured["data"]["client_id"] == "x"
    assert captured["data"]["client_secret"] == "sekret"
    assert captured["data"]["scope"] == "openid email"


def test_refresh_token_calls_kc(kc_token_payload):
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(200, kc_token_payload))
        tok = keycloak_client.refresh_token("r")
    assert tok.refresh_token == "RR"


def test_client_credentials(kc_token_payload):
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(200, kc_token_payload))
        tok = keycloak_client.client_credentials("c", "s", scope="a", audience="b")
    assert tok.access_token == "AA"


def test_introspect_returns_payload():
    payload = {"active": True}
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(200, payload))
        result = keycloak_client.introspect("tok")
    assert result == payload


def test_logout_no_content():
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(204, content=b""))
        keycloak_client.logout("r")


def test_error_response_raises():
    payload = {"error": "x", "error_description": "boom"}
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(401, payload))
        with pytest.raises(keycloak_client.KeycloakError) as exc_info:
            keycloak_client.password_grant("u", "p")
    assert exc_info.value.status_code == 401


def test_transport_error_raises():
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.post.side_effect = httpx.ConnectError("nope")
        MockClient.return_value = client
        with pytest.raises(keycloak_client.KeycloakError):
            keycloak_client.password_grant("u", "p")


def test_well_known_and_jwks():
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(200, {"issuer": "kc"}))
        assert keycloak_client.well_known()["issuer"] == "kc"
        MockClient.return_value = _client_ctx(_fake_response(200, {"keys": []}))
        assert "keys" in keycloak_client.jwks()


def test_well_known_error():
    with patch("core.keycloak_client.httpx.Client") as MockClient:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        resp = _fake_response(500, {})
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=MagicMock(), response=resp
        )
        client.get.return_value = resp
        MockClient.return_value = client
        with pytest.raises(keycloak_client.KeycloakError):
            keycloak_client.well_known()


def test_token_ms_fetch_claims_ok():
    with patch("core.token_ms_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(
            _fake_response(200, {"nome": "X"})
        )
        assert token_ms_client.fetch_claims("u")["nome"] == "X"


def test_token_ms_fetch_claims_404():
    with patch("core.token_ms_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(404, {}))
        assert token_ms_client.fetch_claims("u") == {}


def test_token_ms_fetch_claims_5xx_raises_then_swallows():
    """Implementation choice: 5xx propaga TokenMSError mas é capturado pelo wrapper de view."""
    with patch("core.token_ms_client.httpx.Client") as MockClient:
        MockClient.return_value = _client_ctx(_fake_response(500, {}))
        with pytest.raises(token_ms_client.TokenMSError):
            token_ms_client.fetch_claims("u")


def test_token_ms_unreachable_returns_default():
    with patch("core.token_ms_client.httpx.Client") as MockClient:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get.side_effect = httpx.ConnectError("down")
        MockClient.return_value = client
        assert token_ms_client.fetch_claims("u", default={"k": 1}) == {"k": 1}


def test_audit_publish_falls_back_to_log(caplog):
    with caplog.at_level("INFO", logger="gateway.audit"):
        audit.publish("test.event", {"x": 1})
    assert any("test.event" in r.message for r in caplog.records)
