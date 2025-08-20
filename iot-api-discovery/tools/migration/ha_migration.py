from __future__ import annotations

from typing import Any, Dict, List, Tuple
import json
import re

from database.models import DeviceTwin


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    s = name.casefold().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 _-]", "", s)
    return s


def _list_twins(session, provider: str | None = None) -> List[DeviceTwin]:
    q = session.query(DeviceTwin)
    if provider:
        q = q.filter(DeviceTwin.provider == provider)
    return q.all()


def build_migration_plan(session_factory, provider_preference: List[str] | None = None) -> Dict[str, Any]:
    provider_preference = provider_preference or [
        "zigbee2mqtt",
        "smartthings",
        "openhab",
        "zwave_js",
        "hue",
    ]
    session = session_factory()
    try:
        ha_entities = _list_twins(session, "home_assistant")
        other_twins = [t for t in _list_twins(session) if t.provider != "home_assistant"]
        # index by normalized name per provider
        name_index: Dict[str, Dict[str, DeviceTwin]] = {}
        for t in other_twins:
            pname = t.provider
            name_index.setdefault(pname, {})[_normalize_name(t.name) or _normalize_name(t.external_id)] = t

        plan: List[Dict[str, Any]] = []
        for e in ha_entities:
            ename_norm = _normalize_name(e.name) or _normalize_name(e.external_id)
            e_caps = set(json.loads(e.capabilities or "[]"))
            suggestion: Dict[str, Any] | None = None
            confidence = "none"
            # preference order exact name match
            for prov in provider_preference:
                idx = name_index.get(prov, {})
                candidate = idx.get(ename_norm)
                if candidate:
                    c_caps = set(json.loads(candidate.capabilities or "[]"))
                    missing = list(e_caps - c_caps)
                    suggestion = {
                        "provider": prov,
                        "external_id": candidate.external_id,
                        "name": candidate.name,
                        "missing_capabilities": missing,
                    }
                    confidence = "exact"
                    break
            # fallback contains match
            if not suggestion:
                for prov in provider_preference:
                    idx = name_index.get(prov, {})
                    for key, candidate in idx.items():
                        if ename_norm and ename_norm in key:
                            c_caps = set(json.loads(candidate.capabilities or "[]"))
                            missing = list(e_caps - c_caps)
                            suggestion = {
                                "provider": prov,
                                "external_id": candidate.external_id,
                                "name": candidate.name,
                                "missing_capabilities": missing,
                            }
                            confidence = "contains"
                            break
                    if suggestion:
                        break
            plan.append(
                {
                    "entity": {"provider": e.provider, "external_id": e.external_id, "name": e.name, "capabilities": list(e_caps)},
                    "suggestion": suggestion,
                    "confidence": confidence,
                }
            )
        return {"count": len(plan), "plan": plan}
    finally:
        session.close()

