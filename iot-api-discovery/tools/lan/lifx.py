from __future__ import annotations

import socket
from typing import Any, Dict, List


def discover_lifx(timeout_seconds: int = 2) -> List[Dict[str, Any]]:
    """Discover LIFX bulbs via LAN UDP broadcast (GetService message).

    This sends a minimal packet and listens for any response. For full protocol
    use official SDKs; this is a best-effort probe.
    """
    # LIFX uses UDP/56700; send an empty broadcast and listen for responses
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout_seconds)
    results: List[Dict[str, Any]] = []
    try:
        sock.sendto(b"\x00" * 36, ("255.255.255.255", 56700))
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                results.append({"address": addr[0], "bytes": len(data)})
            except socket.timeout:
                break
    finally:
        sock.close()
    return results

