from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from database.api_database import get_session_factory
from database.models import AutomationRuleModel


@dataclass
class Rule:
    id: str
    trigger: Dict[str, Any]
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    throttle_seconds: Optional[int] = None


class AutomationEngine:
    def __init__(self) -> None:
        self._rules: Dict[str, Rule] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._session_factory = get_session_factory("sqlite:///./iot_discovery.db")
        self._last_fire_time: Dict[str, float] = {}

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())
            await self._load_rules()

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
            self._task = None

    def add_rule(self, rule: Rule) -> None:
        self._rules[rule.id] = rule
        asyncio.create_task(self._persist_rule(rule))

    def remove_rule(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)
        asyncio.create_task(self._delete_rule(rule_id))

    async def emit_event(self, event: Dict[str, Any]) -> None:
        await self._event_queue.put(event)

    async def _loop(self) -> None:
        while True:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._evaluate(event)
            except asyncio.TimeoutError:
                # periodic schedules
                await self._tick_schedules()

    async def _evaluate(self, event: Dict[str, Any]) -> None:
        for rule in list(self._rules.values()):
            if not rule.enabled:
                continue
            if not self._match_trigger(rule.trigger, event):
                continue
            if not all(self._match_condition(c, event) for c in rule.conditions):
                continue
            # Throttling per rule
            if rule.throttle_seconds:
                now = asyncio.get_event_loop().time()
                last = self._last_fire_time.get(rule.id, 0.0)
                if now - last < float(rule.throttle_seconds):
                    continue
            for action in rule.actions:
                await self._execute_action(action, event)
            if rule.throttle_seconds:
                self._last_fire_time[rule.id] = asyncio.get_event_loop().time()

    def evaluate_match(self, trigger: Dict[str, Any], conditions: List[Dict[str, Any]], event: Dict[str, Any]) -> bool:
        if not self._match_trigger(trigger, event):
            return False
        for cond in conditions or []:
            if not self._match_condition(cond, event):
                return False
        return True

    def _match_trigger(self, trigger: Dict[str, Any], event: Dict[str, Any]) -> bool:
        for k, v in trigger.items():
            if event.get(k) != v:
                return False
        return True

    def _match_condition(self, cond: Dict[str, Any], event: Dict[str, Any]) -> bool:
        ctype = cond.get("type")
        try:
            if ctype == "context":
                ctx = event.get("context", {})
                key = cond.get("key")
                if key is None:
                    return False
                val = ctx.get(key)
                if "equals" in cond:
                    return val == cond.get("equals")
                if "in" in cond and isinstance(cond.get("in"), list):
                    return val in cond.get("in")
                if cond.get("present") is True:
                    return key in ctx
                return bool(val)
            if ctype == "twin":
                provider = cond.get("provider")
                external_id = cond.get("external_id")
                path = cond.get("path")
                if not (provider and external_id and path):
                    return False
                value = self._get_twin_value(provider, external_id, path)
                if "equals" in cond:
                    return value == cond.get("equals")
                if "in" in cond and isinstance(cond.get("in"), list):
                    return value in cond.get("in")
                if cond.get("present") is True:
                    return value is not None
                return bool(value)
            if ctype == "time":
                import datetime as _dt
                now = _dt.datetime.now()
                if "after" in cond:
                    hh, mm = map(int, str(cond["after"]).split(":"))
                    t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                    if now < t:
                        return False
                if "before" in cond:
                    hh, mm = map(int, str(cond["before"]).split(":"))
                    t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                    if now > t:
                        return False
                if "weekday_in" in cond and isinstance(cond["weekday_in"], list):
                    if now.weekday() not in cond["weekday_in"]:
                        return False
                return True
            # default
            for k, v in cond.items():
                if event.get(k) != v:
                    return False
            return True
        except Exception:
            return False

    async def _execute_action(self, action: Dict[str, Any], event: Dict[str, Any]) -> None:
        t = action.get("type")
        if t == "http":
            from tools.control.http_control import invoke_http

            await asyncio.to_thread(invoke_http, action.get("endpoint", {}), action.get("payload"))
        elif t == "mqtt":
            from tools.control.mqtt_control import publish_mqtt

            await asyncio.to_thread(
                publish_mqtt,
                action.get("broker", "localhost"),
                action.get("topic", ""),
                action.get("payload", ""),
            )

    async def _load_rules(self) -> None:
        session = self._session_factory()
        try:
            for row in session.query(AutomationRuleModel).all():
                self._rules[row.id] = Rule(
                    id=row.id,
                    trigger=json.loads(row.trigger),
                    conditions=json.loads(row.conditions or "[]"),
                    actions=json.loads(row.actions),
                    enabled=row.enabled,
                    throttle_seconds=None,  # not persisted; can be set at runtime
                )
        finally:
            session.close()

    async def _persist_rule(self, rule: Rule) -> None:
        session = self._session_factory()
        try:
            row = session.get(AutomationRuleModel, rule.id) or AutomationRuleModel(id=rule.id)
            row.enabled = rule.enabled
            row.trigger = json.dumps(rule.trigger)
            row.conditions = json.dumps(rule.conditions or [])
            row.actions = json.dumps(rule.actions)
            session.add(row)
            session.commit()
        finally:
            session.close()

    async def _delete_rule(self, rule_id: str) -> None:
        session = self._session_factory()
        try:
            row = session.get(AutomationRuleModel, rule_id)
            if row:
                session.delete(row)
                session.commit()
        finally:
            session.close()

    async def _tick_schedules(self) -> None:
        session = self._session_factory()
        try:
            rows = session.query(AutomationRuleModel).all()
            now_ts = asyncio.get_event_loop().time()
            for r in rows:
                if not r.enabled:
                    continue
                should_run = False
                import time as _t
                now = _t.time()
                # Cron if present
                if r.cron:
                    try:
                        from croniter import croniter

                        it = croniter(r.cron, r.last_run_at or __import__("datetime").datetime.utcfromtimestamp(now))
                        next_time = it.get_next(float)
                        if r.last_run_at is None or now >= next_time:
                            should_run = True
                    except Exception:
                        pass
                # Interval fallback
                elif r.schedule_interval_seconds:
                    if not r.last_run_at or (now - r.last_run_at.timestamp()) >= r.schedule_interval_seconds:
                        should_run = True
                if should_run:
                    await self._evaluate({"scheduled": r.id})
                    # update last_run_at
                    r.last_run_at = __import__("datetime").datetime.utcnow()
                    session.add(r)
                    session.commit()
        finally:
            session.close()