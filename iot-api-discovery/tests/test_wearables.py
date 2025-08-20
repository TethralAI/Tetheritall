from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import create_app


def test_oura_oauth_url_missing(monkeypatch):
    app = create_app()
    client = TestClient(app)
    r = client.get("/integrations/oura/oauth/url", headers={"X-API-Key": ""})
    assert r.status_code == 400


def test_dynamic_terra(monkeypatch):
    app = create_app()
    client = TestClient(app)
    # Missing API key returns error json
    r = client.get("/integrations/terra/daily?user_id=u1", headers={"X-API-Key": ""})
    assert r.status_code == 200
    assert "error" in r.json()

