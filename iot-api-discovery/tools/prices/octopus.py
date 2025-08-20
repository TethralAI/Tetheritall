from __future__ import annotations

from typing import Any, Dict, List, Tuple
import datetime as _dt
import requests


def fetch_unit_rates(product_code: str, tariff_code: str, page_size: int = 250, timeout: int = 15) -> List[Dict[str, Any]]:
    url = f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
    params = {"page_size": page_size}
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return (r.json() or {}).get("results", [])


def compute_cheap_window(rates: List[Dict[str, Any]], window_minutes: int = 120) -> Tuple[str, str, float]:
    # rates: list of {"valid_from", "valid_to", "value_inc_vat"}
    # compute cheapest contiguous window of given minutes
    # Convert to timeline
    slots: List[Tuple[_dt.datetime, _dt.datetime, float]] = []
    for r in rates or []:
        try:
            start = _dt.datetime.fromisoformat(r["valid_from"].replace("Z", "+00:00"))
            end = _dt.datetime.fromisoformat(r["valid_to"].replace("Z", "+00:00"))
            # Some feeds return ranges reversed; normalize so start <= end
            if end < start:
                start, end = end, start
            price = float(r.get("value_inc_vat") or r.get("value_exc_vat") or 0)
            slots.append((start, end, price))
        except Exception:
            continue
    slots.sort(key=lambda x: x[0])
    window = _dt.timedelta(minutes=window_minutes)
    best_cost = float("inf")
    best_range: Tuple[_dt.datetime, _dt.datetime] | None = None
    # Sliding window across slots
    for i in range(len(slots)):
        start = slots[i][0]
        end_target = start + window
        cost = 0.0
        covered = _dt.timedelta(0)
        t = start
        j = i
        while j < len(slots) and t < end_target:
            s, e, p = slots[j]
            if e <= t:
                j += 1
                continue
            # overlap
            seg_start = max(t, s)
            seg_end = min(e, end_target)
            if seg_end > seg_start:
                minutes = (seg_end - seg_start).total_seconds() / 60.0
                cost += p * minutes
                covered += (seg_end - seg_start)
                t = seg_end
            else:
                t = seg_end
                j += 1
        if covered >= window and cost < best_cost:
            best_cost = cost
            best_range = (start, end_target)
    if not best_range:
        return ("", "", 0.0)
    return (best_range[0].isoformat(), best_range[1].isoformat(), best_cost)

