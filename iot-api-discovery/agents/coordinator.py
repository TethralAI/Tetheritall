"""
Coordinator Agent

Manages workflow between DocumentationHunter and NetworkScanner:
- Priority task queue and concurrent workers
- Passes data between agents
- Stores results in the database
- Provides health/metrics hooks
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .documentation_hunter import DocumentationHunter
from .network_scanner import NetworkScanner
from config.policy import ConsentPolicy
from database.api_database import get_session_factory, create_all
from database.models import Device, ApiEndpoint, AuthenticationMethod, ScanResult


logger = logging.getLogger(__name__)


@dataclass
class CoordinatorConfig:
    max_concurrent_devices: int = 5
    database_url: str = "sqlite:///./iot_discovery.db"


class CoordinatorAgent:
    def __init__(self, config: Optional[CoordinatorConfig] = None) -> None:
        self.config = config or CoordinatorConfig()
        create_all(self.config.database_url)
        self._session_factory = get_session_factory(self.config.database_url)
        self._queue: "asyncio.PriorityQueue[Tuple[int, str, Dict[str, Any]]]" = asyncio.PriorityQueue()
        self._workers: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._status_subscribers: List[asyncio.Queue] = []
        self._tasks_status: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        for _ in range(self.config.max_concurrent_devices):
            self._workers.append(asyncio.create_task(self._worker_loop()))
        logger.info("Coordinator started with %s workers", len(self._workers))

    async def stop(self) -> None:
        self._stop_event.set()
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    def subscribe_status(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._status_subscribers.append(q)
        return q

    def unsubscribe_status(self, q: asyncio.Queue) -> None:
        if q in self._status_subscribers:
            self._status_subscribers.remove(q)

    async def _broadcast(self, message: Dict[str, Any]) -> None:
        for q in list(self._status_subscribers):
            try:
                q.put_nowait(message)
            except Exception:
                # drop failed subscriber
                self.unsubscribe_status(q)

    async def add_task(
        self,
        manufacturer: str,
        model: Optional[str],
        ip_ranges: Optional[List[str]] = None,
        priority: int = 10,
        consent: Optional[ConsentPolicy] = None,
    ) -> str:
        task_id = str(uuid.uuid4())
        payload = {
            "manufacturer": manufacturer,
            "model": model,
            "ip_ranges": ip_ranges or [],
            "consent": consent or ConsentPolicy(),
            "task_id": task_id,
            "created_at": time.time(),
        }
        self._tasks_status[task_id] = {"state": "queued", "payload": {"manufacturer": manufacturer, "model": model}}
        await self._queue.put((priority, task_id, payload))
        await self._broadcast({"type": "enqueued", "task_id": task_id, "priority": priority})
        return task_id

    async def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                priority, task_id, payload = await self._queue.get()
            except asyncio.CancelledError:
                break
            try:
                await self._run_task(task_id, payload)
            except Exception as exc:
                logger.exception("Task %s failed: %s", task_id, exc)
                self._tasks_status[task_id] = {"state": "failed", "error": str(exc)}
                await self._broadcast({"type": "failed", "task_id": task_id, "error": str(exc)})
            finally:
                self._queue.task_done()

    async def _run_task(self, task_id: str, payload: Dict[str, Any]) -> None:
        manufacturer = payload.get("manufacturer")
        model = payload.get("model")
        ip_ranges: List[str] = payload.get("ip_ranges") or []
        consent: ConsentPolicy = payload.get("consent")

        self._tasks_status[task_id] = {"state": "running"}
        await self._broadcast({"type": "started", "task_id": task_id, "manufacturer": manufacturer, "model": model})

        # Documentation discovery
        async with DocumentationHunter(manufacturer=manufacturer, model=model) as hunter:
            doc_data = await hunter.discover()
        await self._broadcast({"type": "documentation", "task_id": task_id, "count_endpoints": len(doc_data.get("endpoints", []))})

        # Network scan with hint
        scanner = NetworkScanner(ip_ranges=ip_ranges, device_hint=doc_data, consent_policy=consent)
        scan_results = await scanner.scan()
        await self._broadcast({"type": "network", "task_id": task_id, "summary": scan_results.get("summary")})

        # Persist results
        device_id = await asyncio.to_thread(self._persist_results, manufacturer, model, doc_data, scan_results)
        self._tasks_status[task_id] = {"state": "completed", "device_id": device_id}
        await self._broadcast({"type": "completed", "task_id": task_id, "device_id": device_id})

    def _persist_results(
        self,
        manufacturer: str,
        model: Optional[str],
        doc: Dict[str, Any],
        scan: Dict[str, Any],
    ) -> int:
        session = self._session_factory()
        try:
            device = Device(model=model or "", manufacturer=manufacturer)
            session.add(device)
            session.flush()

            # Endpoints from documentation
            for ep in doc.get("endpoints", []) or []:
                session.add(
                    ApiEndpoint(
                        device_id=device.id,
                        url=str(ep.get("path", "")),
                        method=str(ep.get("method")) if ep.get("method") else "GET",
                        auth_required=False,
                        success_rate=float(ep.get("confidence") or 0.0),
                    )
                )
            # Auth methods
            for am in doc.get("authentication_methods", []) or []:
                session.add(
                    AuthenticationMethod(
                        device_id=device.id,
                        auth_type=str(am.get("type") or "unknown"),
                        credentials=None,
                        success_rate=float(am.get("confidence") or 0.0),
                    )
                )
            # Raw scan result
            session.add(ScanResult(device_id=device.id, agent_type="coordinator", raw_data=str({"doc": True, "scan": True})))
            session.commit()
            return device.id
        finally:
            session.close()

    # Query helpers for API layer
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        return self._tasks_status.get(task_id, {"state": "unknown"})


