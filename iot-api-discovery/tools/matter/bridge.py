from __future__ import annotations

from typing import Any, Dict, List


def discover_matter_bridges(timeout_seconds: int = 5) -> List[Dict[str, Any]]:
    """Discover Matter bridges via DNS-SD service type _matter._tcp.local.

    Many Zigbee/Z-Wave devices appear exposed via such bridges.
    """
    try:
        from zeroconf import Zeroconf, ServiceBrowser  # type: ignore
    except Exception:
        return []
    results: List[Dict[str, Any]] = []

    class _Listener:
        def add_service(self, zc, st, name):
            info = zc.get_service_info(st, name, timeout=timeout_seconds * 1000)
            if info:
                results.append({
                    "service_type": st,
                    "name": name,
                    "addresses": info.parsed_addresses() if hasattr(info, "parsed_addresses") else [],
                    "host": getattr(info, "server", None),
                })

    zc = Zeroconf()
    try:
        ServiceBrowser(zc, "_matter._tcp.local.", _Listener())
        import time as _t
        _t.sleep(timeout_seconds)
    finally:
        zc.close()
    return results

