from __future__ import annotations

import socket
from typing import Any, Dict, List


def discover_yeelight(timeout_seconds: int = 2) -> List[Dict[str, Any]]:
    """Discover Yeelight bulbs via SSDP-like broadcast."""
    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1982\r\n"
        'MAN: "ssdp:discover"\r\n'
        "ST: wifi_bulb\r\n"
        "\r\n"
    ).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout_seconds)
    results: List[Dict[str, Any]] = []
    try:
        sock.sendto(msg, ("239.255.255.250", 1982))
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                payload = data.decode(errors="ignore")
                results.append({"address": addr[0], "payload": payload})
            except socket.timeout:
                break
    finally:
        sock.close()
    return results

