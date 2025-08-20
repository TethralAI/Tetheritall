from __future__ import annotations

import pytest

from agents.network_scanner import NetworkScanner, NetworkScannerConfig


@pytest.mark.asyncio
async def test_scan_aggregates(monkeypatch):
    scanner = NetworkScanner(ip_ranges=["192.168.1.0/30"], device_hint={})

    async def fake_scan_ports(ranges):
        return [
            {"host": "192.168.1.10", "protocol": "tcp", "port": 80, "service": "http"},
            {"host": "192.168.1.11", "protocol": "tcp", "port": 1883, "service": "mqtt"},
        ]

    async def fake_probe_http(host, port, use_https=False):
        return ([{"host": host, "port": port, "scheme": "http", "path": "/api", "method": "GET"}], [{"type": "http"}])

    async def fake_probe_mqtt(host, port):
        return ([{"host": host, "port": port, "protocol": "mqtt"}], [{"type": "mqtt"}])

    monkeypatch.setattr(scanner, "_scan_ports", fake_scan_ports)
    monkeypatch.setattr(scanner, "_probe_http", fake_probe_http)
    monkeypatch.setattr(scanner, "_probe_mqtt", fake_probe_mqtt)

    result = await scanner.scan()
    assert result["summary"]["num_hosts"] == 2
    assert any(ep.get("scheme") == "http" for ep in result["endpoints"])
    assert any(ep.get("protocol") == "mqtt" for ep in result["endpoints"])
    assert result["metrics"]["http_endpoints"] >= 1
