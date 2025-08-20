from __future__ import annotations

import pytest

from agents.documentation_hunter import DocumentationHunter


def test_extract_from_text_endpoints_and_auth():
    hunter = DocumentationHunter(manufacturer="Acme")
    text = """
    GET /api/v1/devices
    Authorization: Bearer xyz
    ```
    curl -X POST http://example.com/api/v2/login -d '{"u":"x","p":"y"}'
    ```
    API Key required
    """
    extracted = hunter._extract_from_text(text, source="unit-test")
    assert any("/api/" in e["path"] for e in extracted["endpoints"])  # type: ignore[index]
    auth_types = {a["type"] for a in extracted["authentication_methods"]}  # type: ignore[index]
    assert {"bearer", "api_key"} & auth_types
    assert len(extracted["examples"]) >= 1


@pytest.mark.asyncio
async def test_discover_aggregates(monkeypatch):
    hunter = DocumentationHunter(manufacturer="Acme", model="X1")

    async def fake_fetch_json(method, url, *, params=None, headers=None):
        if "api.github.com" in url:
            return {
                "items": [
                    {
                        "full_name": "acme/integration",
                        "html_url": "https://github.com/acme/integration",
                        "stargazers_count": 42,
                        "description": "Client for Acme X1. GET /api/v1/status with API key",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                ]
            }
        # forums
        return {
            "topics": [
                {"slug": "acme-x1", "id": 123, "title": "Bearer token setup /api/auth", "created_at": "2024-01-02"}
            ]
        }

    async def fake_fetch_text(method, url, *, params=None, headers=None):
        return "API docs here: POST /api/v2/login and GET /v1/devices\n```curl -X GET http://host/api/v1/items```"

    monkeypatch.setattr(hunter, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(hunter, "_fetch_text", fake_fetch_text)
    async def _noop_rate_limited():
        return None

    monkeypatch.setattr(hunter, "_rate_limited", _noop_rate_limited)
    monkeypatch.setattr(DocumentationHunter, "_build_candidate_manufacturer_urls", lambda self: ["https://docs.acme.com/api"])  # type: ignore[misc]

    result = await hunter.discover()
    assert result["manufacturer"] == "Acme"
    assert any("/api/" in e.get("path", "") for e in result["endpoints"])  # type: ignore[index]
    auth_types = {a.get("type") for a in result["authentication_methods"]}  # type: ignore[index]
    assert {"bearer", "api_key"} & auth_types
    assert "github" in result["sources"]
    assert "manufacturer" in result["sources"]
    assert "forums" in result["sources"]

