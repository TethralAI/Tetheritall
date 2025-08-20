from __future__ import annotations

from typing import Any, Dict, List


def discover_ssdp(timeout_seconds: int = 3) -> List[Dict[str, Any]]:
    """Discover SSDP/UPnP devices via M-SEARCH."""
    import socket
    import time

    group = ("239.255.255.250", 1900)
    msg = "\r\n".join(
        [
            "M-SEARCH * HTTP/1.1",
            f"HOST: {group[0]}:{group[1]}",
            'MAN: "ssdp:discover"',
            "MX: 2",
            "ST: ssdp:all",
            "\r\n",
        ]
    ).encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout_seconds)
    results: List[Dict[str, Any]] = []
    try:
        sock.sendto(msg, group)
        start = time.time()
        while time.time() - start < timeout_seconds:
            try:
                data, addr = sock.recvfrom(65535)
                payload = data.decode(errors="ignore")
                results.append({"address": addr[0], "payload": payload})
            except socket.timeout:
                break
    finally:
        sock.close()
    return results

