from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import jwt


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
    ORG_ID_HEADER = os.getenv("ORG_ID_HEADER", "X-Org-Id")
    # Token bucket-ish limits (per second) and burst window in seconds
    RL_RPS = int(os.getenv("RL_RPS", "10"))
    RL_BURST = int(os.getenv("RL_BURST", "30"))
    BODY_MAX_BYTES = int(os.getenv("BODY_MAX_BYTES", "65536"))
    STRICT_JSON = os.getenv("STRICT_JSON", "true").lower() == "true"
    CB_FAILS = int(os.getenv("CB_FAILS", "5"))
    CB_COOLDOWN = int(os.getenv("CB_COOLDOWN", "30"))
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")
    ORG_ALLOWLIST = parse_allowlist(os.getenv("ORG_ALLOWLIST"))
    ORG_DENYLIST = parse_allowlist(os.getenv("ORG_DENYLIST"))
    # mTLS
    MTLS_CA = os.getenv("MTLS_CA_PATH")
    MTLS_CERT = os.getenv("MTLS_CLIENT_CERT_PATH")
    MTLS_KEY = os.getenv("MTLS_CLIENT_KEY_PATH")
    # Caching
    CACHE_PREFIXES = [p.strip() for p in (os.getenv("CACHE_GET_PREFIXES") or "").split(",") if p.strip()]
    CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "60"))

    # Simple in-memory RL fallback
    app.state.rate_store = {}
    app.state.cb = {"integrations": {"open_until": 0, "fails": 0}, "automation": {"open_until": 0, "fails": 0}}

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

    def _bucket_key(ip: str, org: str, path: str) -> str:
        return f"rl2:{org}:{ip}:{path}:{int(time.time())}"

    def _verify_jwt(request: Request) -> str:
        if not JWT_SECRET:
            return request.headers.get(ORG_ID_HEADER, "default")
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience=JWT_AUDIENCE) if JWT_AUDIENCE else jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            org = str(payload.get("org") or payload.get("tenant") or request.headers.get(ORG_ID_HEADER) or "default")
            if ORG_DENYLIST and org in ORG_DENYLIST:
                raise HTTPException(status_code=403, detail="org denied")
            if ORG_ALLOWLIST and org not in ORG_ALLOWLIST:
                raise HTTPException(status_code=403, detail="org not allowed")
            return org
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="invalid token")

    @app.middleware("http")
    async def auth_and_rate_limit(request: Request, call_next):
        # API Key allow-list (simple)
        token = request.headers.get("X-API-Key", "")
        if API_TOKEN and token != API_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "invalid api key"})

        # JWT (optional)
        org_id = _verify_jwt(request)

        # Rate limit per-IP using Redis if available else in-memory
        client_ip = request.client.host if request.client else "unknown"
        key = _bucket_key(client_ip, org_id, request.url.path)
        limit = RL_RPS
        try:
            if app.state.redis:
                val = app.state.redis.incr(key)
                if val == 1:
                    app.state.redis.expire(key, 1)
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
    async def _validate_json_body(request: Request) -> bytes | None:
        # Enforce size and JSON object type for mutating requests
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl and int(cl) > BODY_MAX_BYTES:
                raise HTTPException(status_code=413, detail="payload too large")
            body = await request.body()
            if len(body) > BODY_MAX_BYTES:
                raise HTTPException(status_code=413, detail="payload too large")
            if STRICT_JSON and request.headers.get("content-type", "").startswith("application/json"):
                try:
                    import json as _j
                    data = _j.loads(body or b"{}")
                    if not isinstance(data, dict):
                        raise HTTPException(status_code=422, detail="json body must be an object")
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(status_code=400, detail="invalid json")
            return body
        return await request.body()

    def _check_cb(target: str) -> None:
        now = int(time.time())
        st = app.state.cb.get(target, {"open_until": 0, "fails": 0})
        if st["open_until"] > now:
            raise HTTPException(status_code=503, detail=f"{target} unavailable")

    def _record_cb(target: str, success: bool) -> None:
        now = int(time.time())
        st = app.state.cb.get(target, {"open_until": 0, "fails": 0})
        if success:
            st["fails"] = 0
            st["open_until"] = 0
        else:
            st["fails"] = st.get("fails", 0) + 1
            if st["fails"] >= CB_FAILS:
                st["open_until"] = now + CB_COOLDOWN
        app.state.cb[target] = st

    def _mtls_args() -> Dict[str, Any]:
        args: Dict[str, Any] = {}
        if MTLS_CA:
            args["verify"] = MTLS_CA
        if MTLS_CERT and MTLS_KEY:
            args["cert"] = (MTLS_CERT, MTLS_KEY)
        return args

    def _cache_key(url: str) -> str:
        return f"cache:{url}"

    def _cacheable(path: str) -> bool:
        if not CACHE_PREFIXES:
            return False
        for p in CACHE_PREFIXES:
            if path.startswith(p):
                return True
        return False

    async def _maybe_cache_get(path: str, perform_request):
        if not app.state.redis or not _cacheable(path):
            return await perform_request()
        key = _cache_key(path)
        try:
            val = app.state.redis.get(key)
            if val:
                import json as _j
                data = _j.loads(val)
                return JSONResponse(status_code=data.get("status", 200), content=data.get("body", {}))
        except Exception:
            pass
        resp = await perform_request()
        try:
            # only cache 2xx
            if getattr(resp, "status_code", 200) < 300:
                import json as _j
                app.state.redis.setex(key, CACHE_TTL, _j.dumps({"status": resp.status_code, "body": resp.body.decode() if hasattr(resp, 'body') else resp.body}))
        except Exception:
            pass
        return resp

    @app.api_route("/proxy/integrations/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_integrations(path: str, request: Request) -> Any:
        if not INTEGRATIONS_BASE_URL:
            raise HTTPException(status_code=502, detail="integrations not configured")
        target = f"{INTEGRATIONS_BASE_URL}/{path}"
        if not is_allowed_host(target):
            raise HTTPException(status_code=403, detail="outbound host not allowed")
        _check_cb("integrations")

        async def _do():
            async with httpx.AsyncClient(timeout=20, **_mtls_args()) as client:
                body = await _validate_json_body(request)
                headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
                try:
                    resp = await client.request(request.method, target, content=body, headers=headers)
                    _record_cb("integrations", resp.status_code < 500)
                except Exception:
                    _record_cb("integrations", False)
                    raise HTTPException(status_code=502, detail="upstream error")
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text
                return JSONResponse(status_code=resp.status_code, content=data if isinstance(data, dict) else {"data": data})

        if request.method == "GET" and _cacheable(request.url.path):
            return await _maybe_cache_get(request.url.path, _do)
        return await _do()

    @app.api_route("/proxy/automation/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_automation(path: str, request: Request) -> Any:
        if not AUTOMATION_BASE_URL:
            raise HTTPException(status_code=502, detail="automation not configured")
        target = f"{AUTOMATION_BASE_URL}/{path}"
        if not is_allowed_host(target):
            raise HTTPException(status_code=403, detail="outbound host not allowed")
        _check_cb("automation")

        async def _do():
            async with httpx.AsyncClient(timeout=20, **_mtls_args()) as client:
                body = await _validate_json_body(request)
                headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
                try:
                    resp = await client.request(request.method, target, content=body, headers=headers)
                    _record_cb("automation", resp.status_code < 500)
                except Exception:
                    _record_cb("automation", False)
                    raise HTTPException(status_code=502, detail="upstream error")
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text
                return JSONResponse(status_code=resp.status_code, content=data if isinstance(data, dict) else {"data": data})

        if request.method == "GET" and _cacheable(request.url.path):
            return await _maybe_cache_get(request.url.path, _do)
        return await _do()

    return app


app = create_app()

