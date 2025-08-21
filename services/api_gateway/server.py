from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx


def parse_allowlist(env_val: str | None) -> set[str]:
    items = [s.strip().lower() for s in (env_val or "").split(",") if s.strip()]
    return set(items)


def create_app() -> FastAPI:
    app = FastAPI(title="API Gateway (Lite)")

    API_TOKEN = os.getenv("API_TOKEN", "")
    REDIS_URL = os.getenv("REDIS_URL")
    OUTBOUND_ALLOWLIST = parse_allowlist(os.getenv("OUTBOUND_ALLOWLIST"))
    INTEGRATIONS_BASE_URL = os.getenv("INTEGRATIONS_BASE_URL") or os.getenv("INTEGRATIONS_BASE_URL".lower())
    AUTOMATION_BASE_URL = os.getenv("AUTOMATION_BASE_URL")

    # Simple in-memory RL fallback
    app.state.rate_store = {}

    try:
        import redis  # type: ignore
        app.state.redis = redis.Redis.from_url(REDIS_URL) if REDIS_URL else None
    except Exception:
        app.state.redis = None

    def is_allowed_host(url: str) -> bool:
        if not OUTBOUND_ALLOWLIST:
            return True
        try:
            from urllib.parse import urlparse
            host = (urlparse(url).hostname or "").lower()
            return any(host == d or host.endswith("." + d) for d in OUTBOUND_ALLOWLIST)
        except Exception:
            return False

    @app.middleware("http")
    async def auth_and_rate_limit(request: Request, call_next):
        # API Key allow-list (simple)
        token = request.headers.get("X-API-Key", "")
        if API_TOKEN and token != API_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "invalid api key"})

        # Rate limit per-IP using Redis if available else in-memory
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{client_ip}:{int(time.time())//60}"
        limit = 120
        try:
            if app.state.redis:
                val = app.state.redis.incr(key)
                if val == 1:
                    app.state.redis.expire(key, 60)
                if val > limit:
                    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
            else:
                store = app.state.rate_store
                count = store.get(key, 0) + 1
                store[key] = count
                if count > limit:
                    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
        except Exception:
            pass

        return await call_next(request)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"ok": True}

    # Proxy endpoints
    @app.api_route("/proxy/integrations/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_integrations(path: str, request: Request) -> Any:
        if not INTEGRATIONS_BASE_URL:
            raise HTTPException(status_code=502, detail="integrations not configured")
        target = f"{INTEGRATIONS_BASE_URL}/{path}"
        if not is_allowed_host(target):
            raise HTTPException(status_code=403, detail="outbound host not allowed")
        async with httpx.AsyncClient(timeout=20) as client:
            body = await request.body()
            headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
            resp = await client.request(request.method, target, content=body, headers=headers)
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            return JSONResponse(status_code=resp.status_code, content=data if isinstance(data, dict) else {"data": data})

    @app.api_route("/proxy/automation/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_automation(path: str, request: Request) -> Any:
        if not AUTOMATION_BASE_URL:
            raise HTTPException(status_code=502, detail="automation not configured")
        target = f"{AUTOMATION_BASE_URL}/{path}"
        if not is_allowed_host(target):
            raise HTTPException(status_code=403, detail="outbound host not allowed")
        async with httpx.AsyncClient(timeout=20) as client:
            body = await request.body()
            headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
            resp = await client.request(request.method, target, content=body, headers=headers)
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            return JSONResponse(status_code=resp.status_code, content=data if isinstance(data, dict) else {"data": data})

    return app


app = create_app()

