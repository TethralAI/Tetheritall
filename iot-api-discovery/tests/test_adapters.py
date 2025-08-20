from __future__ import annotations

import json
import types

from adapters.usgs import fetch_quakes
from adapters.nws import fetch_alerts


def test_usgs_fetch_quakes_monkeypatch(monkeypatch):
    class DummyResp:
        def __init__(self):
            self._data = {"features": [{"properties": {"title": "M 3.1 quake", "mag": 3.1, "time": 0, "url": "u"}, "geometry": {}}]}

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResp())
    items = fetch_quakes(37.0, -122.0)
    assert items and items[0]["type"] == "earthquake"


def test_nws_fetch_alerts_monkeypatch(monkeypatch):
    class DummyResp:
        def __init__(self):
            self._data = {"features": [{"properties": {"headline": "Alert", "severity": "Severe", "effective": "now", "expires": "later", "areaDesc": "Area", "@id": "id"}}]}

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResp())
    items = fetch_alerts(37.0, -122.0)
    assert items and items[0]["type"] == "weather_alert"

