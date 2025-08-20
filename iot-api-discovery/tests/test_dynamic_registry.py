from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import create_app


def test_ingest_list_and_call(monkeypatch):
    app = create_app()
    client = TestClient(app)

    spec = {
        "manufacturer": "AcmeCloud",
        "endpoints": [
            {"name": "hello", "url": "https://api.acmecloud.test/v1/hello", "method": "GET"}
        ],
    }
    r = client.post("/discover/ingest", json=spec, headers={"X-API-Key": ""})
    assert r.status_code == 200

    r = client.get("/integrations/dynamic/providers", headers={"X-API-Key": ""})
    assert r.status_code == 200 and "acmecloud" in r.json().get("providers", [])

    # Monkeypatch requests.get
    import requests as _rq

    class Dummy:
        ok = True
        status_code = 200
        headers = {"content-type": "application/json"}

        def json(self):
            return {"hello": "world"}

        text = "ok"

    monkeypatch.setattr(_rq, "get", lambda url, **k: Dummy())

    r = client.post(
        "/integrations/dynamic/acmecloud/call",
        json={"endpoint": {"url": "https://api.acmecloud.test/v1/hello", "method": "GET"}},
        headers={"X-API-Key": ""},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") and data.get("status") == 200 and data.get("data", {}).get("hello") == "world"

