from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests


def discover_bridges(timeout: int = 5) -> List[Dict[str, Any]]:
    # Try N-UPnP cloud discovery first
    items: List[Dict[str, Any]] = []
    try:
        r = requests.get("https://discovery.meethue.com/", timeout=timeout)
        if r.ok:
            for b in r.json() or []:
                items.append({
                    "id": b.get("id"),
                    "internalipaddress": b.get("internalipaddress"),
                    "port": b.get("port", 80),
                })
    except Exception:
        pass
    # Try mDNS via zeroconf if available
    try:
        from zeroconf import Zeroconf, ServiceBrowser  # type: ignore

        zc = Zeroconf()
        try:
            results: List[Dict[str, Any]] = []

            class _L:
                def add_service(self, z, st, name):
                    info = z.get_service_info(st, name, timeout=timeout * 1000)
                    if info:
                        ip_list = info.parsed_addresses() if hasattr(info, "parsed_addresses") else []
                        if ip_list:
                            results.append({
                                "name": name,
                                "internalipaddress": ip_list[0],
                                "port": getattr(info, "port", 80),
                            })

            ServiceBrowser(zc, "_hue._tcp.local.", _L())
            import time as _t
            _t.sleep(2)
            # merge results
            seen = {i.get("internalipaddress") for i in items}
            for r in results:
                if r.get("internalipaddress") not in seen:
                    items.append(r)
        finally:
            zc.close()
    except Exception:
        pass
    return items


def pair(bridge_ip: str, app_name: str = "iot-orchestrator", device_name: str = "server") -> Dict[str, Any]:
    url = f"http://{bridge_ip}/api"
    try:
        r = requests.post(url, json={"devicetype": f"{app_name}#{device_name}"}, timeout=10)
        arr = r.json() if r.ok else []
        if isinstance(arr, list) and arr and arr[0].get("success"):
            return {"ok": True, "username": arr[0]["success"].get("username"), "clientkey": arr[0]["success"].get("clientkey")}
        return {"ok": False, "error": arr}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def list_lights(bridge_ip: str, username: str, timeout: int = 10) -> Dict[str, Any]:
    url = f"http://{bridge_ip}/api/{username}/lights"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def set_light_state(bridge_ip: str, username: str, light_id: str, state: Dict[str, Any], timeout: int = 10) -> Any:
    url = f"http://{bridge_ip}/api/{username}/lights/{light_id}/state"
    r = requests.put(url, json=state, timeout=timeout)
    return r.json() if r.ok else {"ok": False, "status": r.status_code}

