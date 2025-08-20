from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import create_app


def test_ha_importer_components(monkeypatch):
    app = create_app()
    client = TestClient(app)

    from tools.importers import home_assistant as imp

    monkeypatch.setattr(imp, "list_components", lambda token=None: [{"name": "light", "path": "homeassistant/components/light"}])
    r = client.get("/importers/home_assistant/components", headers={"X-API-Key": ""})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1

    monkeypatch.setattr(imp, "fetch_manifest", lambda comp, token=None: {"domain": comp, "name": "Light", "iot_class": "local_polling"})
    r = client.get("/importers/home_assistant/manifest?component=light", headers={"X-API-Key": ""})
    assert r.status_code == 200
    assert r.json()["manifest"]["domain"] == "light"

