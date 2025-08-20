from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from database.models import AutomationRuleModel
from config.settings import settings


def _is_ha_call_action(action: Dict[str, Any]) -> bool:
    if action.get("type") != "http":
        return False
    endpoint = action.get("endpoint", {})
    url = (endpoint.get("url") or "").lower()
    return "/integrations/home_assistant/call" in url


def _ha_entity_from_action(action: Dict[str, Any]) -> str | None:
    payload = action.get("payload", {})
    pl = payload.get("payload") if isinstance(payload, dict) else None
    if isinstance(pl, dict):
        eid = pl.get("entity_id")
        if isinstance(eid, str):
            return eid
    return None


def _ha_service_from_action(action: Dict[str, Any]) -> str | None:
    payload = action.get("payload", {})
    if isinstance(payload, dict):
        svc = payload.get("service")
        if isinstance(svc, str):
            return svc
    return None


def _build_action_for_target(provider: str, external_id: str, service: str) -> Dict[str, Any] | None:
    svc = service.lower()
    if provider == "zigbee2mqtt":
        topic = f"zigbee2mqtt/{external_id}/set"
        if svc in ("turn_on", "on", "switch_on"):
            return {"type": "mqtt", "broker": settings.z2m_broker or "localhost", "topic": topic, "payload": json.dumps({"state": "ON"})}
        if svc in ("turn_off", "off", "switch_off"):
            return {"type": "mqtt", "broker": settings.z2m_broker or "localhost", "topic": topic, "payload": json.dumps({"state": "OFF"})}
    if provider == "smartthings":
        if svc in ("turn_on", "on", "switch_on"):
            cmd = "on"
        elif svc in ("turn_off", "off", "switch_off"):
            cmd = "off"
        else:
            return None
        return {
            "type": "http",
            "endpoint": {"url": "http://localhost:8000/integrations/smartthings/commands", "method": "POST"},
            "payload": {"device_id": external_id, "commands": [{"component": "main", "capability": "switch", "command": cmd}]},
        }
    return None


def rewrite_rules(session_factory, mappings: List[Dict[str, str]], dry_run: bool = True) -> Dict[str, Any]:
    """Rewrite rules replacing HA call actions with provider-native actions.

    mappings: list of {"ha_entity_id", "target_provider", "target_external_id"}
    """
    # Build mapping dict
    map_by_eid = {m["ha_entity_id"]: (m["target_provider"], m["target_external_id"]) for m in mappings}
    session = session_factory()
    changed: List[str] = []
    backup: Dict[str, Any] = {}
    try:
        rows = session.query(AutomationRuleModel).all()
        for r in rows:
            try:
                actions = json.loads(r.actions)
            except Exception:
                continue
            updated = False
            new_actions: List[Dict[str, Any]] = []
            for a in actions or []:
                if _is_ha_call_action(a):
                    eid = _ha_entity_from_action(a)
                    svc = _ha_service_from_action(a) or ""
                    if eid and eid in map_by_eid:
                        provider, ext = map_by_eid[eid]
                        repl = _build_action_for_target(provider, ext, svc)
                        if repl:
                            new_actions.append(repl)
                            updated = True
                            continue
                new_actions.append(a)
            if updated:
                changed.append(r.id)
                backup[r.id] = actions
                if not dry_run:
                    r.actions = json.dumps(new_actions)
                    session.add(r)
        if not dry_run and changed:
            session.commit()
        # Save backup file
        backup_path = None
        if backup:
            ts = int(time.time())
            d = os.path.expanduser("~/.iot_api_discovery")
            try:
                os.makedirs(d, exist_ok=True)
                backup_path = os.path.join(d, f"rules_backup_{ts}.json")
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(backup, f)
            except Exception:
                backup_path = None
        return {"changed_rules": changed, "count": len(changed), "backup_path": backup_path}
    finally:
        session.close()


def rollback_rules(session_factory, backup: Dict[str, Any]) -> Dict[str, Any]:
    session = session_factory()
    restored: List[str] = []
    try:
        for rule_id, actions in (backup or {}).items():
            row = session.get(AutomationRuleModel, rule_id)
            if not row:
                continue
            row.actions = json.dumps(actions)
            session.add(row)
            restored.append(rule_id)
        if restored:
            session.commit()
        return {"restored": restored, "count": len(restored)}
    finally:
        session.close()

