from __future__ import annotations

from typing import Any, Dict, List


def discover_smartthings_mdns(timeout_seconds: int = 5) -> List[Dict[str, Any]]:
    """Discover SmartThings hubs via mDNS/DNS-SD (best-effort)."""
    try:
        from zeroconf import Zeroconf, ServiceBrowser  # type: ignore
    except Exception:
        return []
    results: List[Dict[str, Any]] = []

    class _Listener:
        def add_service(self, zc, st, name):
            info = zc.get_service_info(st, name, timeout=timeout_seconds * 1000)
            if info and "smartthings" in (str(info.server) or "").lower():
                results.append({
                    "service_type": st,
                    "name": name,
                    "addresses": info.parsed_addresses() if hasattr(info, "parsed_addresses") else [],
                    "host": getattr(info, "server", None),
                })

    zc = Zeroconf()
    try:
        ServiceBrowser(zc, "_services._dns-sd._udp.local.", _Listener())
        import time as _t
        _t.sleep(timeout_seconds)
    finally:
        zc.close()
    return results

