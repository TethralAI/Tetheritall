from __future__ import annotations

import os
import re
import time
import json
from typing import Any, Dict, List, Tuple

from config.settings import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None


PII_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"\+?\d[\d\s().-]{7,}\d")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]


def _parse_budgets(spec: str | None) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for item in (spec or "").split(","):
        if not item.strip():
            continue
        k, _, v = item.partition(":")
        try:
            out[k.strip() or "default"] = int(v)
        except Exception:
            continue
    return out


class LLMAudit:
    def __init__(self) -> None:
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None

    def log(self, org_id: str, entry: Dict[str, Any]) -> None:
        key = f"audit:llm:{org_id or 'default'}"
        try:
            if self._rds:
                self._rds.lpush(key, json.dumps(entry))
                self._rds.ltrim(key, 0, 999)
            else:
                # In-memory fallback on app state not available here; best-effort env var
                pass
        except Exception:
            pass


class LLMGuard:
    def __init__(self) -> None:
        self._budgets = _parse_budgets(settings.llm_budgets)
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None
        self._audit = LLMAudit()

    def _budget_key(self, org_id: str) -> str:
        return f"budget:llm:{org_id or 'default'}:{time.strftime('%Y%m%d')}"

    def _get_quota(self, org_id: str) -> int:
        return self._budgets.get(org_id, self._budgets.get("default", 0))

    def pii_scrub(self, text: str) -> str:
        out = text
        for label, pat in PII_PATTERNS:
            out = pat.sub(f"<{label}>", out)
        return out

    def check_and_consume(self, org_id: str, cost: int) -> bool:
        quota = self._get_quota(org_id)
        if quota <= 0:
            return True  # unlimited or disabled
        key = self._budget_key(org_id)
        try:
            if self._rds:
                val = self._rds.incrby(key, cost)
                if val == cost:
                    self._rds.expire(key, 86400)
                return val <= quota
            else:
                # No Redis: naive in-memory fallback via env not feasible here; allow
                return True
        except Exception:
            return True

    def log_audit(self, org_id: str, payload: Dict[str, Any]) -> None:
        self._audit.log(org_id, payload)

    def is_tool_allowed(self, name: str) -> bool:
        allowlist = {s.strip() for s in (settings.llm_allowed_tools or "").split(",") if s.strip()}
        return not allowlist or name in allowlist

