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
from typing import Any, Dict, List, Optional, Tuple, Callable
import os

from .documentation_hunter import DocumentationHunter
from .network_scanner import NetworkScanner
from config.policy import ConsentPolicy
from database.api_database import get_session_factory, create_all
from database.models import Device, ApiEndpoint, AuthenticationMethod, ScanResult, Task as TaskModel


logger = logging.getLogger(__name__)


@dataclass
class CoordinatorConfig:
    max_concurrent_devices: int = 5
    database_url: str = "sqlite:///./iot_discovery.db"
    # Dynamic scaling
    min_workers: int = 1
    max_workers: int = 10
    scale_up_queue_per_worker: int = 2
    scale_down_idle_seconds: int = 20
    scaler_interval_seconds: int = 5
    # Edge/cloud offload
    remote_workers: List[str] = None  # type: ignore[assignment]
    enable_edge_offload: bool = True
    scheduling_policy: str = "auto"  # on_device | edge | cloud | auto


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
        self._last_activity_ts: float = time.time()
        if self.config.remote_workers is None:
            self.config.remote_workers = []

        # Providers for agent execution paths
        self._network_scan_providers: List[Callable[[Dict[str, Any]], "asyncio.Future"]] = []

    async def start(self) -> None:
        initial_workers = max(self.config.min_workers, 1)
        for _ in range(initial_workers):
            self._workers.append(asyncio.create_task(self._worker_loop()))
        logger.info("Coordinator started with %s workers", len(self._workers))
        # Start scaler loop
        asyncio.create_task(self._scaler_loop())

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
        # Persist task for durability
        await asyncio.to_thread(self._persist_task, task_id, manufacturer, model, priority, payload)
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
                self._last_activity_ts = time.time()

    async def _scaler_loop(self) -> None:
        """Dynamically scale worker pool based on queue depth and system load."""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.config.scaler_interval_seconds)
                qsize = self._queue.qsize()
                num_workers = len(self._workers)
                load_ok = self._system_load_ok()
                # Scale up
                if load_ok and qsize > num_workers * self.config.scale_up_queue_per_worker and num_workers < self.config.max_workers:
                    self._workers.append(asyncio.create_task(self._worker_loop()))
                    await self._broadcast({"type": "scale", "action": "up", "workers": len(self._workers)})
                # Scale down if idle
                idle = (time.time() - self._last_activity_ts) > self.config.scale_down_idle_seconds
                if idle and num_workers > self.config.min_workers:
                    # Cancel one worker
                    task = self._workers.pop()
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    await self._broadcast({"type": "scale", "action": "down", "workers": len(self._workers)})
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Scaler loop error: %s", exc)

    def _system_load_ok(self) -> bool:
        # Try psutil if present, else fallback to os.getloadavg
        try:
            import psutil  # type: ignore

            cpu = psutil.cpu_percent(interval=0)  # non-blocking snapshot
            return cpu < 80.0
        except Exception:
            try:
                load1, _, _ = os.getloadavg()
                cpus = os.cpu_count() or 1
                return (load1 / cpus) < 1.0
            except Exception:
                return True

    async def _run_task(self, task_id: str, payload: Dict[str, Any]) -> None:
        manufacturer = payload.get("manufacturer")
        model = payload.get("model")
        ip_ranges: List[str] = payload.get("ip_ranges") or []
        consent: ConsentPolicy = payload.get("consent")

        self._tasks_status[task_id] = {"state": "running"}
        await asyncio.to_thread(self._update_task_state, task_id, "running")
        await self._broadcast({"type": "started", "task_id": task_id, "manufacturer": manufacturer, "model": model})

        # Documentation discovery
        async with DocumentationHunter(manufacturer=manufacturer, model=model) as hunter:
            doc_data = await hunter.discover()
        await self._broadcast({"type": "documentation", "task_id": task_id, "count_endpoints": len(doc_data.get("endpoints", []))})

        # Network scan provider selection (on-device/edge/cloud/auto)
        scan_results: Dict[str, Any]
        policy = getattr(self.config, "scheduling_policy", "auto")
        if policy == "on_device":
            scanner = NetworkScanner(ip_ranges=ip_ranges, device_hint=doc_data, consent_policy=consent)
            scan_results = await scanner.scan()
        elif policy in ("edge", "cloud") and self.config.enable_edge_offload and self.config.remote_workers:
            scan_results = await self._offload_network_scan(doc_data, ip_ranges, consent)
        else:
            # auto: prefer edge if system under load and remotes available, else local
            if not self._system_load_ok() and self.config.remote_workers and self.config.enable_edge_offload:
                try:
                    scan_results = await self._offload_network_scan(doc_data, ip_ranges, consent)
                except Exception:
                    scanner = NetworkScanner(ip_ranges=ip_ranges, device_hint=doc_data, consent_policy=consent)
                    scan_results = await scanner.scan()
            else:
                scanner = NetworkScanner(ip_ranges=ip_ranges, device_hint=doc_data, consent_policy=consent)
                scan_results = await scanner.scan()
        await self._broadcast({"type": "network", "task_id": task_id, "summary": scan_results.get("summary")})

        # Persist results
        device_id = await asyncio.to_thread(self._persist_results, manufacturer, model, doc_data, scan_results)
        self._tasks_status[task_id] = {"state": "completed", "device_id": device_id}
        await asyncio.to_thread(self._update_task_state, task_id, "completed")
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
            session.add(ScanResult(device_id=device.id, agent_type="coordinator", raw_data=str({"doc": True, "scan": True, "summary": scan.get("summary")})))
            session.commit()
            return device.id
        finally:
            session.close()

    # Query helpers for API layer
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        return self._tasks_status.get(task_id, {"state": "unknown"})

    # Durable tasks
    def _persist_task(self, task_id: str, manufacturer: str, model: Optional[str], priority: int, payload: Dict[str, Any]) -> None:
        session = self._session_factory()
        try:
            tm = TaskModel(id=task_id, manufacturer=manufacturer, model=model, priority=priority, state="queued", payload=str(payload))
            session.add(tm)
            session.commit()
        finally:
            session.close()

    def _update_task_state(self, task_id: str, state: str) -> None:
        session = self._session_factory()
        try:
            tm = session.get(TaskModel, task_id)
            if tm:
                tm.state = state
                tm.updated_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()

    async def _offload_network_scan(
        self,
        doc_data: Dict[str, Any],
        ip_ranges: List[str],
        consent: ConsentPolicy,
    ) -> Dict[str, Any]:
        """Offload network scanning to an edge/cloud worker via HTTP.

        Protocol: POST {worker}/scan with JSON {ip_ranges, device_hint, consent, testing}
        Returns scanning result JSON.
        """
        import random
        import json
        import aiohttp

        if not self.config.remote_workers:
            raise RuntimeError("No remote workers configured")
        url = random.choice(self.config.remote_workers).rstrip("/") + "/scan"
        payload = {
            "ip_ranges": ip_ranges,
            "device_hint": doc_data,
            "consent": {k: getattr(consent, k) for k in vars(consent) if not k.startswith("_")},
            "testing": getattr(consent, "testing_mode", False),
        }
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                return await resp.json()


