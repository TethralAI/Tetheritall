from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from tools.events.bus import bus
from config.settings import settings
from database.api_database import get_session_factory, session_scope
from database.models import DeviceTwin, DeviceTwinVersion, AuditEvent, Outbox

GROUP = "workers"
CONSUMER = "worker-1"

SessionFactory = get_session_factory(settings.database_url)


async def process_event(event: Dict[str, Any]) -> None:
    topic = event.get("topic")
    payload = event.get("payload", {})
    try:
        if isinstance(payload, str):
            payload = json.loads(payload)
    except Exception:
        payload = {}

    with session_scope(SessionFactory) as session:
        session.add(AuditEvent(kind=f"event:{topic}", payload=json.dumps(payload)))

        if topic == "smartthings.device_event":
            device_id = payload.get("deviceId")
            display_name = payload.get("displayName")
            capability = payload.get("capability")
            value = payload.get("value")
            if not device_id:
                return
            twin = (
                session.query(DeviceTwin)
                .filter(DeviceTwin.provider == "smartthings", DeviceTwin.external_id == device_id)
                .one_or_none()
            )
            from datetime import datetime

            import json as _j

            state_obj: Dict[str, Any] = {}
            caps_list: list[str] = []
            if capability:
                state_obj[capability] = value
                caps_list = [capability]

            state_json = _j.dumps(state_obj)
            caps_json = _j.dumps(caps_list)

            if twin is None:
                twin = DeviceTwin(
                    provider="smartthings",
                    external_id=device_id,
                    name=display_name,
                    state=state_json,
                    capabilities=caps_json,
                    updated_at=datetime.utcnow(),
                    version=1,
                )
                session.add(twin)
                session.flush()
                session.add(
                    DeviceTwinVersion(
                        twin_id=twin.id,
                        version=1,
                        diff=None,
                        full=state_json,
                        event_id=payload.get("eventId"),
                    )
                )
            else:
                twin.version = (twin.version or 0) + 1
                twin.name = display_name or twin.name
                twin.state = state_json
                twin.capabilities = caps_json
                twin.updated_at = datetime.utcnow()
                session.add(
                    DeviceTwinVersion(
                        twin_id=twin.id,
                        version=twin.version,
                        diff=None,
                        full=state_json,
                        event_id=payload.get("eventId"),
                    )
                )


async def outbox_publisher_loop() -> None:
    while True:
        with session_scope(SessionFactory) as session:
            from datetime import datetime

            pending = (
                session.query(Outbox)
                .order_by(Outbox.available_at.asc())
                .limit(20)
                .all()
            )
            for row in pending:
                try:
                    payload = json.loads(row.payload) if isinstance(row.payload, str) else row.payload
                except Exception:
                    payload = {}
                published_id = bus.publish(row.topic, payload or {})
                row.attempts = (row.attempts or 0) + 1
                row.available_at = datetime.utcnow()
                if (row.attempts or 0) >= 10:
                    session.delete(row)
                    continue
                if published_id:
                    session.delete(row)
        await asyncio.sleep(1.0)


async def run_worker() -> None:
    # Start NATS subscription if using NATS
    if settings.event_bus_backend.lower() == "nats":
        async def _handle(subject: str, data: Dict[str, Any]) -> None:
            await process_event({"topic": subject, "payload": data})
        await bus.subscribe_nats("smartthings.device_event", _handle)
        # Keep running loops
        while True:
            await asyncio.sleep(1.0)

    # Else Redis consumer
    bus.ensure_consumer_group(GROUP)
    async def consume_loop() -> None:
        while True:
            entries = bus.read_group(GROUP, CONSUMER, count=10, block_ms=1000)
            for entry_id, fields in entries:
                try:
                    event = {k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in fields.items()}
                    await process_event(event)
                    bus.ack(GROUP, entry_id)
                except Exception as exc:
                    pass
            await asyncio.sleep(0.1)

    await asyncio.gather(consume_loop(), outbox_publisher_loop())


if __name__ == "__main__":
    asyncio.run(run_worker())