from __future__ import annotations

from typing import Any, Dict, List


def discover_mdns(timeout_seconds: int = 5) -> List[Dict[str, Any]]:
    """Discover mDNS (Zeroconf) services on the local network.

    Returns a list of dicts with keys: host, service_type, name, addresses.
    """
    try:
        from zeroconf import Zeroconf, ServiceBrowser  # type: ignore
    except Exception:
        return []

    results: List[Dict[str, Any]] = []

    class _Listener:
        def add_service(self, zc: Any, service_type: str, name: str) -> None:
            try:
                info = zc.get_service_info(service_type, name, timeout=timeout_seconds * 1000)
                if info:
                    addrs = []
                    for a in info.parsed_addresses():
                        addrs.append(a)
                    results.append({
                        "service_type": service_type,
                        "name": name,
                        "addresses": addrs,
                        "host": info.server if hasattr(info, "server") else None,
                    })
            except Exception:
                return

    zc = Zeroconf()
    try:
        # Browse common mDNS service types
        service_types = ["_http._tcp.local.", "_hap._tcp.local.", "_mqtt._tcp.local.", "_coap._udp.local."]
        browsers = [ServiceBrowser(zc, st, _Listener()) for st in service_types]
        import time as _t
        _t.sleep(timeout_seconds)
    finally:
        zc.close()
    return results

