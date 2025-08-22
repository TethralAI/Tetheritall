from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None

try:
    import asyncio
    from nats.aio.client import Client as NATS  # type: ignore
except Exception:
    NATS = None  # type: ignore

try:
    from kafka import KafkaProducer, KafkaConsumer  # type: ignore
except Exception:
    KafkaProducer = None  # type: ignore
    KafkaConsumer = None  # type: ignore

try:
    from prometheus_client import Counter
except Exception:
    Counter = None  # type: ignore


STREAM_KEY = settings.events_stream_key or "events:stream"

_events_published = None
_events_consumed = None
if Counter is not None:
    _events_published = Counter("events_published_total", "Events published", ["backend", "topic"])
    _events_consumed = Counter("events_consumed_total", "Events consumed", ["backend", "topic"])


class EventBus:
    def __init__(self) -> None:
        self.backend = (settings.event_bus_backend or "redis").lower()
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None
        self._nats = None
        self._kafka_producer = None
        # Redis retention (approximate with MAXLEN ~)
        if self.backend == "redis" and self._rds:
            try:
                self._rds.xadd(STREAM_KEY, {"init": 1}, maxlen=settings.events_maxlen, approximate=True)
            except Exception:
                pass

    def _record_pub(self, topic: str) -> None:
        try:
            if _events_published is not None:
                _events_published.labels(self.backend, topic).inc()
        except Exception:
            pass

    def _record_consume(self, topic: str) -> None:
        try:
            if _events_consumed is not None:
                _events_consumed.labels(self.backend, topic).inc()
        except Exception:
            pass

    def health(self) -> Dict[str, Any]:
        ok = True
        detail: Dict[str, Any] = {"backend": self.backend}
        try:
            if self.backend == "redis":
                pong = self._rds.ping() if self._rds else False
                ok = bool(pong)
                detail["redis"] = {"ping": bool(pong)}
            elif self.backend == "nats":
                detail["nats"] = {"connected": bool(self._nats and getattr(self._nats, "_connected", False))}
            elif self.backend == "kafka":
                detail["kafka"] = {"producer": bool(self._kafka_producer is not None)}
        except Exception as exc:
            ok = False
            detail["error"] = str(exc)
        return {"ok": ok, "detail": detail}

    def publish(self, topic: str, payload: Dict[str, Any]) -> Optional[str]:
        self._record_pub(topic)
        if self.backend == "redis":
            if not self._rds:
                return None
            try:
                data = {"topic": topic, "ts": int(time.time()), "payload": json.dumps(payload)}
                return self._rds.xadd(STREAM_KEY, data, maxlen=settings.events_maxlen, approximate=True)
            except Exception:
                return None
        elif self.backend == "nats":
            if NATS is None:
                return None
            # Lazy connect
            try:
                if self._nats is None:
                    self._nats = NATS()
                    # Best-effort connect
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(self._nats.connect(settings.nats_url or "nats://localhost:4222"))
                self._nats.publish(topic.encode(), json.dumps(payload).encode())  # type: ignore[attr-defined]
                return "nats"
            except Exception:
                return None
        elif self.backend == "kafka":
            if KafkaProducer is None:
                return None
            try:
                if self._kafka_producer is None:
                    self._kafka_producer = KafkaProducer(bootstrap_servers=(settings.kafka_bootstrap_servers or "localhost:9092").split(","), value_serializer=lambda v: json.dumps(v).encode())
                self._kafka_producer.send(topic, payload)
                return "kafka"
            except Exception:
                return None
        return None

    def ensure_consumer_group(self, group: str) -> None:
        if self.backend == "redis":
            if not self._rds:
                return
            try:
                self._rds.xgroup_create(name=STREAM_KEY, groupname=group, id="$", mkstream=True)
            except Exception:
                pass
        # NATS/Kafka use different mechanisms; assume topics exist

    def read_group(self, group: str, consumer: str, count: int = 10, block_ms: int = 1000) -> List[Tuple[str, Dict[bytes, bytes]]]:
        if self.backend == "redis":
            if not self._rds:
                return []
            try:
                res = self._rds.xreadgroup(group, consumer, {STREAM_KEY: ">"}, count=count, block=block_ms)
                if not res:
                    return []
                _, entries = res[0]
                return entries
            except Exception:
                return []
        # For non-redis backends, not implemented in this worker path yet
        return []

    def ack(self, group: str, entry_id: str) -> None:
        if self.backend == "redis":
            if not self._rds:
                return
            try:
                self._rds.xack(STREAM_KEY, group, entry_id)
            except Exception:
                pass


bus = EventBus()