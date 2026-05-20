import pytest


@pytest.mark.django_db
def test_health_liveness(api_client):
    resp = api_client.get("/api/health/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.django_db
def test_health_readiness(api_client):
    resp = api_client.get("/api/health/ready/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
