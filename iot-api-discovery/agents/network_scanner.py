"""
Network Scanner Agent

Scans IP ranges, detects services (HTTP, MQTT, CoAP), probes common IoT API
endpoints, attempts auth, validates responses, and produces metrics plus test
cases. Integrates python-nmap, requests, paho-mqtt, aiocoap.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


@dataclass
class NetworkScannerConfig:
    scan_timeout_seconds: int = 30
    max_concurrent_scans: int = 50
    http_request_timeout_seconds: int = 10
    retries: int = 1
    nmap_ports: str = "80,443,8080,8443,1883,8883,5683,5684"
    common_paths: List[str] = None  # type: ignore[assignment]
    common_basic_credentials: List[Tuple[str, str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.common_paths is None:
            self.common_paths = [
                "/api",
                "/rest",
                "/v1",
                "/v2",
                "/swagger.json",
                "/openapi.json",
            ]
        if self.common_basic_credentials is None:
            self.common_basic_credentials = [
                ("admin", "admin"),
                ("admin", "password"),
                ("root", "root"),
                ("user", "user"),
            ]


class NetworkScanner:
    def __init__(
        self,
        ip_ranges: List[str],
        device_hint: Optional[Dict[str, Any]] = None,
        config: Optional[NetworkScannerConfig] = None,
    ) -> None:
        self.ip_ranges = ip_ranges
        self.device_hint = device_hint or {}
        self.config = config or NetworkScannerConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_scans)

    async def scan(self) -> Dict[str, Any]:
        logger.info("Starting network scan for ranges: %s", ", ".join(self.ip_ranges))
        services = await self._scan_ports(self.ip_ranges)
        endpoints, test_cases = await self._probe_services(services)
        metrics = self._compute_metrics(services, endpoints)
        summary = {
            "targets": self.ip_ranges,
            "num_hosts": len({s["host"] for s in services}),
            "endpoints_found": len(endpoints),
            "success_rate": metrics.get("overall_success_rate", 0.0),
        }
        # Enrich with local discovery (best-effort)
        local = await asyncio.gather(
            asyncio.to_thread(self._discover_mdns),
            asyncio.to_thread(self._discover_ssdp),
            asyncio.to_thread(self._read_arp),
            return_exceptions=True,
        )
        local_discovery: Dict[str, Any] = {"mdns": [], "ssdp": [], "arp": []}
        if isinstance(local[0], list):
            local_discovery["mdns"] = local[0]
        if isinstance(local[1], list):
            local_discovery["ssdp"] = local[1]
        if isinstance(local[2], list):
            local_discovery["arp"] = local[2]

        return {
            "summary": summary,
            "services": services,
            "endpoints": endpoints,
            "metrics": metrics,
            "test_cases": test_cases,
            "local": local_discovery,
        }

    async def _scan_ports(self, ranges: List[str]) -> List[Dict[str, Any]]:
        async def run_nmap() -> List[Dict[str, Any]]:
            try:
                import nmap  # type: ignore

                scanner = nmap.PortScanner()
                scanner.scan(
                    hosts=" ".join(ranges),
                    ports=self.config.nmap_ports,
                    arguments=f"-sT -T4 --max-retries {self.config.retries} --host-timeout {self.config.scan_timeout_seconds}s",
                )
                results: List[Dict[str, Any]] = []
                for host in scanner.all_hosts():
                    for proto in ("tcp", "udp"):
                        if proto not in scanner[host]:
                            continue
                        for port, pdata in scanner[host][proto].items():
                            if pdata.get("state") == "open":
                                results.append(
                                    {
                                        "host": host,
                                        "protocol": proto,
                                        "port": int(port),
                                        "service": pdata.get("name"),
                                    }
                                )
                return results
            except Exception as exc:
                logger.warning("nmap scan failed: %s", exc)
                return []

        return await asyncio.to_thread(run_nmap)

    async def _probe_services(self, services: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        endpoints: List[Dict[str, Any]] = []
        test_cases: List[Dict[str, Any]] = []

        async def handle_service(svc: Dict[str, Any]) -> None:
            host = svc["host"]
            port = int(svc["port"])
            proto = svc.get("protocol", "tcp")
            name = (svc.get("service") or "").lower()
            try:
                if port in (80, 8080) or name in ("http", "http-proxy"):
                    eps, tcs = await self._probe_http(host, port, use_https=False)
                    endpoints.extend(eps)
                    test_cases.extend(tcs)
                elif port in (443, 8443) or name in ("https",):
                    eps, tcs = await self._probe_http(host, port, use_https=True)
                    endpoints.extend(eps)
                    test_cases.extend(tcs)
                elif port in (1883, 8883) or "mqtt" in name:
                    eps, tcs = await self._probe_mqtt(host, port)
                    endpoints.extend(eps)
                    test_cases.extend(tcs)
                elif port in (5683, 5684) or "coap" in name:
                    eps, tcs = await self._probe_coap(host, port)
                    endpoints.extend(eps)
                    test_cases.extend(tcs)
            except Exception as exc:
                logger.debug("Probe error for %s:%s - %s", host, port, exc)

        await asyncio.gather(*(handle_service(s) for s in services))
        return endpoints, test_cases

    async def _probe_http(self, host: str, port: int, *, use_https: bool) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        scheme = "https" if use_https else "http"
        base = f"{scheme}://{host}:{port}"
        eps: List[Dict[str, Any]] = []
        tcs: List[Dict[str, Any]] = []

        async def fetch(path: str, auth: Optional[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
            url = base + path
            try:
                def _do_request():
                    return requests.request(
                        method="GET",
                        url=url,
                        timeout=self.config.http_request_timeout_seconds,
                        auth=auth,
                        allow_redirects=True,
                        headers={"User-Agent": "IoT-Scanner/1.0"},
                    )

                resp = await asyncio.to_thread(_do_request)
            except Exception as exc:
                return None
            ok = resp.ok and resp.status_code < 400
            if ok:
                entry = {
                    "host": host,
                    "port": port,
                    "scheme": scheme,
                    "path": path,
                    "method": "GET",
                    "status": resp.status_code,
                    "auth_used": bool(auth),
                    "confidence": 0.8 if auth else 0.7,
                }
                return entry
            return None

        tasks = []
        for path in self.config.common_paths:
            tasks.append(fetch(path, None))
            for cred in self.config.common_basic_credentials:
                tasks.append(fetch(path, cred))

        results = await asyncio.gather(*tasks)
        for r in results:
            if r:
                eps.append(r)
                tcs.append(
                    {
                        "type": "http",
                        "request": {
                            "method": "GET",
                            "url": f"{base}{r['path']}",
                            "auth": r["auth_used"],
                        },
                        "expected": {"status_lt": 400},
                    }
                )
        return eps, tcs

    async def _probe_mqtt(self, host: str, port: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        eps: List[Dict[str, Any]] = []
        tcs: List[Dict[str, Any]] = []
        try:
            import paho.mqtt.client as mqtt  # type: ignore

            def try_connect(username: Optional[str], password: Optional[str]) -> bool:
                client = mqtt.Client()
                if username and password:
                    client.username_pw_set(username=username, password=password)
                client.connect_timeout = self.config.scan_timeout_seconds
                try:
                    rc = client.connect(host, port, keepalive=10)
                    client.disconnect()
                    return rc == 0
                except Exception:
                    return False

            # No auth first, then common creds
            successes = 0
            attempts = 0
            if try_connect(None, None):
                successes += 1
                attempts += 1
                eps.append({"host": host, "port": port, "protocol": "mqtt", "auth_used": False, "confidence": 0.7})
            else:
                attempts += 1
            for user, pwd in self.config.common_basic_credentials:
                if try_connect(user, pwd):
                    successes += 1
                    eps.append({"host": host, "port": port, "protocol": "mqtt", "auth_used": True, "confidence": 0.8})
                attempts += 1
            if attempts:
                tcs.append(
                    {
                        "type": "mqtt",
                        "request": {"host": host, "port": port},
                        "expected": {"connect": True},
                    }
                )
        except Exception as exc:
            logger.debug("MQTT probe error for %s:%s - %s", host, port, exc)
        return eps, tcs

    async def _probe_coap(self, host: str, port: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        eps: List[Dict[str, Any]] = []
        tcs: List[Dict[str, Any]] = []
        try:
            import aiocoap  # type: ignore

            async def get_well_known() -> Optional[Dict[str, Any]]:
                try:
                    protocol = await aiocoap.Context.create_client_context()
                    req = aiocoap.Message(code=aiocoap.codes.Code.GET, uri=f"coap://{host}:{port}/.well-known/core")
                    resp = await asyncio.wait_for(protocol.request(req).response, timeout=self.config.scan_timeout_seconds)
                    if getattr(resp, "code", None) and int(resp.code) // 100 == 2:
                        return {"host": host, "port": port, "protocol": "coap", "path": "/.well-known/core", "confidence": 0.7}
                except Exception:
                    return None
                return None

            res = await get_well_known()
            if res:
                eps.append(res)
                tcs.append(
                    {
                        "type": "coap",
                        "request": {"method": "GET", "uri": f"coap://{host}:{port}/.well-known/core"},
                        "expected": {"code_class": 2},
                    }
                )
        except Exception as exc:
            logger.debug("CoAP probe error for %s:%s - %s", host, port, exc)
        return eps, tcs

    def _compute_metrics(self, services: List[Dict[str, Any]], endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        http_count = sum(1 for e in endpoints if e.get("scheme") in ("http", "https"))
        mqtt_count = sum(1 for e in endpoints if e.get("protocol") == "mqtt")
        coap_count = sum(1 for e in endpoints if e.get("protocol") == "coap")
        total = len(endpoints)
        return {
            "http_endpoints": http_count,
            "mqtt_endpoints": mqtt_count,
            "coap_endpoints": coap_count,
            "overall_success_rate": float(total > 0) * min(1.0, (http_count + mqtt_count + coap_count) / max(total, 1)),
        }

    # Local discovery wrappers
    def _discover_mdns(self) -> List[Dict[str, Any]]:
        try:
            from tools.discovery.mdns import discover_mdns
            return discover_mdns()
        except Exception:
            return []

    def _discover_ssdp(self) -> List[Dict[str, Any]]:
        try:
            from tools.discovery.ssdp import discover_ssdp
            return discover_ssdp()
        except Exception:
            return []

    def _read_arp(self) -> List[Dict[str, Any]]:
        try:
            from tools.discovery.arp import read_arp_table
            return read_arp_table()
        except Exception:
            return []

