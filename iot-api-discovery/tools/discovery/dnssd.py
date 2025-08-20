from __future__ import annotations

from typing import Any, Dict, List


def discover_dnssd(service_types: List[str] | None = None, timeout_seconds: int = 5) -> List[Dict[str, Any]]:
    """DNS-SD discovery via zeroconf (Bonjour) for given service types.

    Defaults to common IoT types (Matter, HAP/HomeKit, HTTP).
    """
    try:
        from zeroconf import Zeroconf, ServiceBrowser  # type: ignore
    except Exception:
        return []
    if service_types is None:
        service_types = ["_matter._tcp.local.", "_hap._tcp.local.", "_http._tcp.local."]

    results: List[Dict[str, Any]] = []

    class _Listener:
        def add_service(self, zc: Any, st: str, name: str) -> None:
            try:
                info = zc.get_service_info(st, name, timeout=timeout_seconds * 1000)
                if info:
                    results.append(
                        {
                            "service_type": st,
                            "name": name,
                            "addresses": info.parsed_addresses() if hasattr(info, "parsed_addresses") else [],
                            "host": getattr(info, "server", None),
                        }
                    )
            except Exception:
                return

    zc = Zeroconf()
    try:
        browsers = [ServiceBrowser(zc, st, _Listener()) for st in service_types]
        import time as _t

        _t.sleep(timeout_seconds)
    finally:
        zc.close()
    return results

