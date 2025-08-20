from __future__ import annotations

from fastapi.testclient import TestClient

from api.server import create_app


def test_hazards_merge(monkeypatch):
    from adapters import usgs as _usgs
    from adapters import nws as _nws

    monkeypatch.setattr(_usgs, "fetch_quakes", lambda lat, lon, **k: [{"severity": 3.0, "title": "M3", "source": "usgs", "time": 1, "url": "u"}])
    monkeypatch.setattr(_nws, "fetch_alerts", lambda lat, lon: [{"severity": "Severe", "title": "Storm", "source": "nws", "effective": "now", "url": "v"}])

    app = create_app()
    client = TestClient(app)
    headers = {"X-API-Key": ""}
    r = client.get("/api/hazards?lat=37.0&lon=-122.0", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    cats = {h["category"] for h in data["hazards"]}
    assert {"seismic", "weather"}.issubset(cats)

