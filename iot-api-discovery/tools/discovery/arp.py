from __future__ import annotations

from typing import Any, Dict, List


def read_arp_table() -> List[Dict[str, Any]]:
    """Read the local ARP table (Linux) from /proc/net/arp if available."""
    results: List[Dict[str, Any]] = []
    try:
        with open("/proc/net/arp", "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        for line in lines[1:]:
            parts = [p for p in line.split() if p]
            if len(parts) >= 6:
                ip, hw_type, flags, mac, mask, iface = parts[:6]
                results.append({"ip": ip, "mac": mac, "iface": iface})
    except Exception:
        pass
    return results

