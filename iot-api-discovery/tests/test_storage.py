from __future__ import annotations

import json
import os

from storage.local_store import save_json


def test_save_json(tmp_path):
    discovery = {
        "manufacturer": "Acme",
        "model": "X1",
        "sources": {},
        "endpoints": [{"path": "/api/v1/devices", "method": "GET"}],
        "authentication_methods": [{"type": "api_key"}],
        "examples": [],
    }
    path = save_json(discovery, directory=str(tmp_path))
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["manufacturer"] == "Acme"
