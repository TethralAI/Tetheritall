from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple
import requests
from config.settings import settings
try:
    import redis  # type: ignore
except Exception:
    redis = None

_cache: Dict[Tuple[int, int], Tuple[float, List[Dict[str, Any]]]] = {}


def fetch_quakes(lat: float, lon: float, min_magnitude: float = 2.5, max_km: int = 150, cache_ttl: int = 60) -> List[Dict[str, Any]]:
    key = (round(lat * 100), round(lon * 100))
    now = time.time()
    if key in _cache and now - _cache[key][0] < cache_ttl:
        return _cache[key][1]
    params = {
        "format": "geojson",
        "latitude": lat,
        "longitude": lon,
        "maxradiuskm": max_km,
        "minmagnitude": min_magnitude,
        "orderby": "time",
    }
    try:
        # Redis cache
        if settings.redis_url and redis is not None:
            try:
                rds = redis.Redis.from_url(settings.redis_url)
                ckey = f"usgs:{lat:.2f}:{lon:.2f}:{min_magnitude}:{max_km}"
                cval = rds.get(ckey)
                if cval:
                    import json as _j
                    return _j.loads(cval)
            except Exception:
                pass
        r = requests.get("https://earthquake.usgs.gov/fdsnws/event/1/query", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        feats = data.get("features", [])
        items: List[Dict[str, Any]] = []
        for f in feats:
            props = f.get("properties", {})
            geom = f.get("geometry", {})
            items.append(
                {
                    "type": "earthquake",
                    "source": "usgs",
                    "title": props.get("title"),
                    "severity": props.get("mag"),
                    "time": props.get("time"),
                    "url": props.get("url"),
                    "geometry": geom,
                }
            )
        _cache[key] = (now, items)
        if settings.redis_url and redis is not None:
            try:
                rds = redis.Redis.from_url(settings.redis_url)
                import json as _j
                rds.setex(ckey, cache_ttl, _j.dumps(items))
            except Exception:
                pass
        return items
    except Exception:
        return []

