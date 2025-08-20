"""
Coordinator Agent

Coordinates the workflow between documentation and network scanning agents,
and will later integrate with the database and API layers.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .documentation_hunter import DocumentationHunter, DocumentationHunterConfig
from .network_scanner import NetworkScanner, NetworkScannerConfig


logger = logging.getLogger(__name__)


@dataclass
class CoordinatorConfig:
    max_concurrent_devices: int = 5


class CoordinatorAgent:
    def __init__(self, config: Optional[CoordinatorConfig] = None) -> None:
        self.config = config or CoordinatorConfig()
        self._device_semaphore = asyncio.Semaphore(self.config.max_concurrent_devices)

    async def process_device(self, manufacturer: str, model: Optional[str] = None) -> Dict[str, Any]:
        async with self._device_semaphore:
            async with DocumentationHunter(manufacturer=manufacturer, model=model) as hunter:
                doc_data = await hunter.discover()

            ip_ranges = []  # Placeholder: derive from documentation hints
            scanner = NetworkScanner(ip_ranges=ip_ranges, device_hint=doc_data)
            scan_results = await scanner.scan()

            return {"documentation": doc_data, "network": scan_results}

