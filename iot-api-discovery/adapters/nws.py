from __future__ import annotations

from typing import Any, Dict, List
import requests
from config.settings import settings
try:
    import redis  # type: ignore
except Exception:
    redis = None


def fetch_alerts(lat: float, lon: float) -> List[Dict[str, Any]]:
    try:
        url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
        headers = {"User-Agent": "IoT-Orchestrator/1.0 (contact@example.com)"}
        # Redis cache
        if settings.redis_url and redis is not None:
            try:
                rds = redis.Redis.from_url(settings.redis_url)
                ckey = f"nws:{lat:.2f}:{lon:.2f}"
                cval = rds.get(ckey)
                if cval:
                    import json as _j
                    return _j.loads(cval)
            except Exception:
                pass
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        items: List[Dict[str, Any]] = []
        for f in data.get("features", []):
            props = f.get("properties", {})
            items.append(
                {
                    "type": "weather_alert",
                    "source": "nws",
                    "title": props.get("headline"),
                    "severity": props.get("severity"),
                    "effective": props.get("effective"),
                    "expires": props.get("expires"),
                    "area": props.get("areaDesc"),
                    "url": props.get("@id"),
                }
            )
        if settings.redis_url and redis is not None:
            try:
                rds = redis.Redis.from_url(settings.redis_url)
                import json as _j
                rds.setex(ckey, 60, _j.dumps(items))
            except Exception:
                pass
        return items
    except Exception:
        return []

