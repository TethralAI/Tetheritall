from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from database.models import DeviceTwin


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    s = name.casefold().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 _-]", "", s)
    return s


def _capabilities(twin: DeviceTwin) -> List[str]:
    try:
        return list(json.loads(twin.capabilities or "[]"))
    except Exception:
        return []


def _state_keys(twin: DeviceTwin) -> List[str]:
    try:
        st = json.loads(twin.state or "{}")
        if isinstance(st, dict):
            return list(st.keys()) + list((st.get("attributes") or {}).keys())
    except Exception:
        pass
    return []


def build_signal_profile(twin: DeviceTwin) -> Dict[str, Any]:
    return {
        "provider": twin.provider,
        "external_id": twin.external_id,
        "name": twin.name,
        "capabilities": _capabilities(twin),
        "state_keys": _state_keys(twin),
    }


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb) or 1
    return inter / union


def _name_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # token overlap
    ta, tb = set(a.split()), set(b.split())
    inter = len(ta & tb)
    union = len(ta | tb) or 1
    return inter / union


def suggest_mappings(session_factory, source_provider: str = "home_assistant", top_k: int = 3) -> List[Dict[str, Any]]:
    session = session_factory()
    try:
        sources = (
            session.query(DeviceTwin)
            .filter(DeviceTwin.provider == source_provider)
            .all()
        )
        targets = [t for t in session.query(DeviceTwin).all() if t.provider != source_provider]
        # Precompute indices
        idx_by_provider: Dict[str, List[DeviceTwin]] = {}
        for t in targets:
            idx_by_provider.setdefault(t.provider, []).append(t)
        out: List[Dict[str, Any]] = []
        for s in sources:
            s_name = _normalize_name(s.name) or _normalize_name(s.external_id)
            s_caps = _capabilities(s)
            s_keys = _state_keys(s)
            candidates: List[Tuple[float, DeviceTwin]] = []
            for prov, twins in idx_by_provider.items():
                for t in twins:
                    t_name = _normalize_name(t.name) or _normalize_name(t.external_id)
                    t_caps = _capabilities(t)
                    t_keys = _state_keys(t)
                    score = (
                        0.6 * _name_similarity(s_name, t_name)
                        + 0.3 * _jaccard(s_caps, t_caps)
                        + 0.1 * _jaccard(s_keys, t_keys)
                    )
                    # penalize wildly different capability sizes
                    if s_caps and t_caps and abs(len(s_caps) - len(t_caps)) >= 3:
                        score *= 0.9
                    if score > 0:
                        candidates.append((score, t))
            candidates.sort(key=lambda x: x[0], reverse=True)
            top = candidates[:top_k]
            out.append(
                {
                    "source": build_signal_profile(s),
                    "suggestions": [
                        {
                            "provider": t.provider,
                            "external_id": t.external_id,
                            "name": t.name,
                            "capabilities": _capabilities(t),
                            "score": round(score, 3),
                        }
                        for score, t in top
                    ],
                }
            )
        return out
    finally:
        session.close()


def build_ui_schema(twin: DeviceTwin) -> Dict[str, Any]:
    caps = set(_capabilities(twin))
    controls: List[Dict[str, Any]] = []
    # Common toggle
    if any(c in caps for c in ("light", "switch", "fan", "lock", "vacuum")):
        controls.append({"type": "toggle", "id": "power", "label": "Power"})
    # Light-specific
    if "light" in caps:
        controls.append({"type": "slider", "id": "brightness", "label": "Brightness", "min": 0, "max": 255})
        controls.append({"type": "slider", "id": "color_temp", "label": "Color Temp", "min": 153, "max": 500})
    # Climate/thermostat
    if "thermostat" in caps or "temperature" in caps:
        controls.append({"type": "slider", "id": "temperature", "label": "Temperature", "min": 10, "max": 30})
        controls.append({"type": "select", "id": "hvac_mode", "label": "Mode", "options": ["off", "heat", "cool", "auto"]})
    # Cover
    if "cover" in caps:
        controls.append({"type": "slider", "id": "position", "label": "Position", "min": 0, "max": 100})
    # Fan
    if "fan" in caps:
        controls.append({"type": "slider", "id": "percentage", "label": "Speed", "min": 0, "max": 100})
    # Media
    if "media" in caps:
        controls.append({"type": "button_group", "id": "media", "buttons": [
            {"id": "play", "label": "Play"}, {"id": "pause", "label": "Pause"}
        ]})
        controls.append({"type": "slider", "id": "volume", "label": "Volume", "min": 0, "max": 100})
    # Sensors (read-only)
    if "sensor" in caps or "binary_sensor" in caps:
        controls.append({"type": "readonly", "id": "state", "label": "State"})
    schema = {
        "provider": twin.provider,
        "external_id": twin.external_id,
        "name": twin.name,
        "controls": controls,
    }
    return schema

