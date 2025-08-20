from __future__ import annotations

import subprocess
from typing import Any, Dict, List


def list_wifi_networks() -> List[Dict[str, Any]]:
    """List nearby WiFi SSIDs using nmcli/iwlist if available. Best-effort."""
    try:
        # Try nmcli first
        out = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"], timeout=5)
        lines = out.decode(errors="ignore").splitlines()
        results: List[Dict[str, Any]] = []
        for line in lines:
            parts = line.split(":")
            if len(parts) >= 3:
                ssid, signal, security = parts[0], parts[1], parts[2]
                if ssid:
                    results.append({"ssid": ssid, "signal": signal, "security": security})
        if results:
            return results
    except Exception:
        pass
    # Fallback or no results
    return []

