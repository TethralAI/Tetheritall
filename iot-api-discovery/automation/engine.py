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


class AutomationEngine:
    def __init__(self) -> None:
        self._rules: Dict[str, Rule] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._session_factory = get_session_factory("sqlite:///./iot_discovery.db")

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
            event = await self._event_queue.get()
            await self._evaluate(event)

    async def _evaluate(self, event: Dict[str, Any]) -> None:
        for rule in list(self._rules.values()):
            if not rule.enabled:
                continue
            if not self._match_trigger(rule.trigger, event):
                continue
            if not all(self._match_condition(c, event) for c in rule.conditions):
                continue
            for action in rule.actions:
                await self._execute_action(action, event)

    def _match_trigger(self, trigger: Dict[str, Any], event: Dict[str, Any]) -> bool:
        for k, v in trigger.items():
            if event.get(k) != v:
                return False
        return True

    def _match_condition(self, cond: Dict[str, Any], event: Dict[str, Any]) -> bool:
        for k, v in cond.items():
            if event.get(k) != v:
                return False
        return True

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