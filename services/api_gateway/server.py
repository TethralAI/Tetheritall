from __future__ import annotations

import asyncio
import os
import time
import json
import secrets
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import jwt
from jsonschema import validate as jsonschema_validate, ValidationError

# Optional OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
except Exception:
    trace = None  # type: ignore

try:
    from prometheus_client import Histogram, Counter
except Exception:
    Histogram = None  # type: ignore
    Counter = None  # type: ignore

from fastapi.middleware.cors import CORSMiddleware
import hmac

_req_hist = None
_cache_hits = None
_cache_misses = None
if Histogram is not None:
    _req_hist = Histogram(
        "gateway_request_duration_seconds",
        "Gateway request duration",
        labelnames=("method", "path", "status"),
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
    )
if Counter is not None:
    _cache_hits = Counter("gateway_cache_hits_total", "Gateway cache hits", ["path"])  # type: ignore
    _cache_misses = Counter("gateway_cache_misses_total", "Gateway cache misses", ["path"])  # type: ignore


def _current_trace_id() -> Optional[str]:
    try:
        if trace is None:
            return None
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if not ctx or not ctx.trace_id:
            return None
        return f"{ctx.trace_id:032x}"
    except Exception:
        return None


def _init_tracing(service_name: str) -> None:
    if trace is None:
        return
    try:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "http://localhost:4318"
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPHTTPExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument()
        HTTPXClientInstrumentor().instrument()
        RedisInstrumentor().instrument()
    except Exception:
        pass


def parse_allowlist(env_val: str | None) -> set[str]:
    items = [s.strip().lower() for s in (env_val or "").split(",") if s.strip()]
    return set(items)


def create_app() -> FastAPI:
    app = FastAPI(title="API Gateway (Lite)")
    _init_tracing("gateway")

    # CORS and security headers
    ALLOW_ORIGINS = [o.strip() for o in (os.getenv("CORS_ALLOW_ORIGINS") or "").split(",") if o.strip()]
    if ALLOW_ORIGINS:
        app.add_middleware(CORSMiddleware, allow_origins=ALLOW_ORIGINS, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = "default-src 'none'"
        return resp

    API_TOKEN = os.getenv("API_TOKEN", "")
    API_TOKENS = [t.strip() for t in (os.getenv("API_TOKENS") or "").split(",") if t.strip()]
    if API_TOKEN:
        API_TOKENS.append(API_TOKEN)
    app.state.api_tokens = set(API_TOKENS)

    REDIS_URL = os.getenv("REDIS_URL")
    OUTBOUND_ALLOWLIST = parse_allowlist(os.getenv("OUTBOUND_ALLOWLIST"))
    INTEGRATIONS_BASE_URL = os.getenv("INTEGRATIONS_BASE_URL") or os.getenv("INTEGRATIONS_BASE_URL".lower())
    AUTOMATION_BASE_URL = os.getenv("AUTOMATION_BASE_URL")
    ORG_ID_HEADER = os.getenv("ORG_ID_HEADER", "X-Org-Id")
    ORG_ROLES_HEADER = os.getenv("ORG_ROLES_HEADER", "X-Org-Roles")
    # Token bucket-ish limits (per second) and burst window in seconds
    RL_RPS = int(os.getenv("RL_RPS", "10"))
    RL_BURST = int(os.getenv("RL_BURST", "30"))
    BODY_MAX_BYTES = int(os.getenv("BODY_MAX_BYTES", "65536"))
    STRICT_JSON = os.getenv("STRICT_JSON", "true").lower() == "true"
    STRICT_RESPONSE_SCHEMA = os.getenv("STRICT_RESPONSE_SCHEMA", "false").lower() == "true"
    CB_FAILS = int(os.getenv("CB_FAILS", "5"))
    CB_COOLDOWN = int(os.getenv("CB_COOLDOWN", "30"))
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")
    ORG_ALLOWLIST = parse_allowlist(os.getenv("ORG_ALLOWLIST"))
    ORG_DENYLIST = parse_allowlist(os.getenv("ORG_DENYLIST"))
    JWKS_URL = os.getenv("JWKS_URL")
    JWKS_CACHE_SECONDS = int(os.getenv("JWKS_CACHE_SECONDS", "300"))
    # mTLS
    MTLS_CA = os.getenv("MTLS_CA_PATH")
    MTLS_CERT = os.getenv("MTLS_CLIENT_CERT_PATH")
    MTLS_KEY = os.getenv("MTLS_CLIENT_KEY_PATH")
    # Caching
    CACHE_PREFIXES = [p.strip() for p in (os.getenv("CACHE_GET_PREFIXES") or "").split(",") if p.strip()]
    CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "60"))
    CACHE_INVALIDATE_PREFIXES = [p.strip() for p in (os.getenv("CACHE_INVALIDATE_PREFIXES") or "").split(",") if p.strip()]
    # Idempotency
    IDEMP_TTL = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "3600"))
    # Schema registry
    SCHEMA_FILE = os.getenv("GATEWAY_SCHEMA_FILE")
    # Quotas (per org)
    QUOTA_HOURLY = int(os.getenv("QUOTA_HOURLY", "10000"))
    QUOTA_DAILY = int(os.getenv("QUOTA_DAILY", "100000"))
    # RBAC policies (JSON string or file)
    RBAC_POLICIES_ENV = os.getenv("RBAC_POLICIES")
    RBAC_POLICIES_FILE = os.getenv("RBAC_POLICIES_FILE")

    def _api_key_valid(presented: str) -> bool:
        if not app.state.api_tokens:
            return True
        for token in app.state.api_tokens:
            try:
                if hmac.compare_digest(presented, token):
                    return True
            except Exception:
                continue
        return False

    # Request timing middleware with exemplars
    if _req_hist is not None:
        @app.middleware("http")
        async def _metrics_timing(request: Request, call_next):
            start = time.time()
            resp = await call_next(request)
            dur = time.time() - start
            labels = (request.method, request.url.path, str(getattr(resp, "status_code", 200)))
            ex = {}
            tid = _current_trace_id()
            if tid:
                ex = {"trace_id": tid}
            try:
                _req_hist.labels(*labels).observe(dur, exemplar=ex or None)  # type: ignore[arg-type]
            except Exception:
                _req_hist.labels(*labels).observe(dur)
            return resp

    # Redis / Sentinel
    try:
        import redis  # type: ignore
        sentinel_cfg = os.getenv("REDIS_SENTINEL")
        sentinel_master = os.getenv("REDIS_SENTINEL_MASTER")
        if sentinel_cfg and sentinel_master:
            from redis.sentinel import Sentinel  # type: ignore
            hosts = []
            for item in sentinel_cfg.split(","):
                host, _, port = item.partition(":")
                hosts.append((host.strip(), int(port or 26379)))
            snt = Sentinel(hosts, socket_timeout=0.5)
            app.state.redis = snt.master_for(sentinel_master)
        else:
            app.state.redis = redis.Redis.from_url(REDIS_URL) if REDIS_URL else None
    except Exception:
        app.state.redis = None

    app.state.jwks = {"fetched": 0, "keys": {}}
    app.state.schemas = []
    app.state.rbac = {"policies": []}

    # Load schema registry (optional). Format: [{"path_prefix": "/capability/smartthings", "request_schema": {...}, "response_schema": {...}}]
    if SCHEMA_FILE and os.path.exists(SCHEMA_FILE):
        try:
            with open(SCHEMA_FILE, "r") as f:
                app.state.schemas = json.load(f)
        except Exception:
            app.state.schemas = []

    # Load RBAC policies
    def _load_rbac() -> None:
        data: Any = None
        if RBAC_POLICIES_ENV:
            try:
                data = json.loads(RBAC_POLICIES_ENV)
            except Exception:
                data = None
        if data is None and RBAC_POLICIES_FILE and os.path.exists(RBAC_POLICIES_FILE):
            try:
                with open(RBAC_POLICIES_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                data = None
        if isinstance(data, dict) and isinstance(data.get("policies"), list):
            app.state.rbac = data
        else:
            app.state.rbac = {"policies": []}

    _load_rbac()

    def _match_schema(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        for entry in app.state.schemas or []:
            prefix = entry.get("path_prefix", "")
            if prefix and path.startswith(prefix):
                return entry.get("request_schema"), entry.get("response_schema")
        return None, None

    # Versioned OpenAPI
    @app.get("/openapi/v1.json")
    async def openapi_v1() -> Any:
        return app.openapi()

    def _error(code: str, status: int, message: str, details: Dict[str, Any] | None = None) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details or {}}})

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

    async def _fetch_jwks() -> None:
        if not JWKS_URL:
            return
        now = int(time.time())
        if now - app.state.jwks.get("fetched", 0) < JWKS_CACHE_SECONDS:
            return
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(JWKS_URL)
                if r.status_code == 200:
                    data = r.json()
                    keys = {k["kid"]: k for k in data.get("keys", []) if "kid" in k}
                    app.state.jwks = {"fetched": now, "keys": keys}
        except Exception:
            pass

    @app.post("/admin/jwks/refresh")
    async def admin_jwks_refresh(request: Request) -> Dict[str, Any]:
        token = request.headers.get("X-API-Key", "")
        if not _api_key_valid(token):
            raise HTTPException(status_code=401, detail="invalid api key")
        # force next fetch by resetting cache time
        app.state.jwks["fetched"] = 0
        await _fetch_jwks()
        return {"ok": True, "keys": list(app.state.jwks.get("keys", {}).keys())}

    def _key_for_kid(kid: str) -> Any | None:
        k = app.state.jwks.get("keys", {}).get(kid)
        if not k:
            return None
        try:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
        except Exception:
            return None

    def _make_traceparent() -> str:
        version = "00"
        trace_id = secrets.token_hex(16)
        parent_id = secrets.token_hex(8)
        flags = "01"
        return f"{version}-{trace_id}-{parent_id}-{flags}"

    async def _verify_jwt(request: Request) -> str:
        if JWKS_URL:
            await _fetch_jwks()
        if not JWT_SECRET and not JWKS_URL:
            return request.headers.get(ORG_ID_HEADER, "default")
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = auth.split(" ", 1)[1]
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg")
            if JWKS_URL and header.get("kid"):
                key = _key_for_kid(header["kid"]) or JWT_SECRET
                payload = jwt.decode(token, key=key, algorithms=[alg] if alg else ["RS256", "HS256"], audience=JWT_AUDIENCE) if JWT_AUDIENCE else jwt.decode(token, key=key, algorithms=[alg] if alg else ["RS256", "HS256"])  # type: ignore[arg-type]
            else:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[alg] if alg else ["HS256"], audience=JWT_AUDIENCE) if JWT_AUDIENCE else jwt.decode(token, JWT_SECRET, algorithms=[alg] if alg else ["HS256"])  # type: ignore[arg-type]
            org = str(payload.get("org") or payload.get("tenant") or request.headers.get(ORG_ID_HEADER) or "default")
            if ORG_DENYLIST and org in ORG_DENYLIST:
                raise HTTPException(status_code=403, detail="org denied")
            if ORG_ALLOWLIST and org not in ORG_ALLOWLIST:
                raise HTTPException(status_code=403, detail="org not allowed")
            # attach roles to request state for downstream RBAC
            roles = payload.get("roles")
            request.state.org_roles = roles if isinstance(roles, list) else None
            return org
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="invalid token")

    def _idempotency_key(path: str, key: str) -> str:
        return f"idem:{path}:{key}"

    async def _get_idempotent_response(path: str, key: str) -> JSONResponse | None:
        if not app.state.redis or not key:
            return None
        try:
            val = app.state.redis.get(_idempotency_key(path, key))
            if val:
                data = json.loads(val)
                return JSONResponse(status_code=data.get("status", 200), content=data.get("body", {}))
        except Exception:
            return None
        return None

    def _store_idempotent_response(path: str, key: str, response: JSONResponse) -> None:
        if not app.state.redis or not key:
            return
        try:
            payload = {"status": response.status_code, "body": getattr(response, "body", b"").decode() if hasattr(response, "body") else response.body}
            app.state.redis.setex(_idempotency_key(path, key), IDEMP_TTL, json.dumps(payload))
        except Exception:
            pass

    def _is_mutating(method: str) -> bool:
        return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}

    def _quota_keys(org: str) -> Tuple[str, str]:
        now = int(time.time())
        hour = now // 3600
        day = now // 86400
        return (f"quota:hour:{org}:{hour}", f"quota:day:{org}:{day}")

    def _quota_inc(org: str) -> Optional[int]:
        try:
            if app.state.redis:
                hk, dk = _quota_keys(org)
                hv = app.state.redis.incr(hk)
                dv = app.state.redis.incr(dk)
                if hv == 1:
                    app.state.redis.expire(hk, 3600)
                if dv == 1:
                    app.state.redis.expire(dk, 86400)
                return max(hv, dv)
            # in-memory fallback
            hk, dk = _quota_keys(org)
            store = app.state.quota_store
            hv = store.get(hk, 0) + 1
            dv = store.get(dk, 0) + 1
            store[hk] = hv
            store[dk] = dv
            return max(hv, dv)
        except Exception:
            return None

    def _quota_check(org: str) -> None:
        hv, dv = 0, 0
        try:
            if app.state.redis:
                hk, dk = _quota_keys(org)
                hv = int(app.state.redis.get(hk) or 0)
                dv = int(app.state.redis.get(dk) or 0)
            else:
                hk, dk = _quota_keys(org)
                hv = int(app.state.quota_store.get(hk, 0))
                dv = int(app.state.quota_store.get(dk, 0))
        except Exception:
            hv, dv = 0, 0
        if hv > QUOTA_HOURLY or dv > QUOTA_DAILY:
            raise HTTPException(status_code=429, detail="quota exceeded")

    def _get_roles(request: Request) -> list[str]:
        if getattr(request.state, "org_roles", None):
            roles = request.state.org_roles
            if isinstance(roles, list):
                return [str(r).lower() for r in roles]
        raw = request.headers.get(ORG_ROLES_HEADER, "")
        return [r.strip().lower() for r in raw.split(",") if r.strip()]

    def _rbac_check(org: str, roles: list[str], method: str, path: str) -> None:
        # Default allow if no policies
        policies = app.state.rbac.get("policies", [])
        if not policies:
            return
        # Evaluate deny-first then allow
        decided: Optional[bool] = None
        for pol in policies:
            orgs = pol.get("orgs") or []
            if orgs and org not in orgs:
                continue
            methods = [m.upper() for m in (pol.get("methods") or [])]
            if methods and method.upper() not in methods:
                continue
            prefixes = pol.get("path_prefixes") or []
            if prefixes and not any(path.startswith(p) for p in prefixes):
                continue
            req_roles = [str(r).lower() for r in (pol.get("roles") or [])]
            if req_roles and not any(r in roles for r in req_roles):
                continue
            effect = (pol.get("effect") or "allow").lower()
            if effect == "deny":
                decided = False
            elif effect == "allow":
                decided = True
        if decided is False:
            raise HTTPException(status_code=403, detail="forbidden by rbac policy")
        # If no allow matched and some policies exist for this path, deny by default
        if decided is None:
            matching = [pol for pol in policies if any(path.startswith(p) for p in (pol.get("path_prefixes") or []))]
            if matching:
                raise HTTPException(status_code=403, detail="forbidden by rbac policy")

    def _cache_key(path: str, org: str) -> str:
        return f"cache:{org}:{path}"

    def _cacheable(path: str) -> bool:
        if not CACHE_PREFIXES:
            return False
        for p in CACHE_PREFIXES:
            if path.startswith(p):
                return True
        return False

    def _invalidate_cache(prefixes: list[str], org: str | None = None) -> None:
        if not app.state.redis:
            return
        try:
            pat = f"cache:{org or '*'}:*"
            for key in app.state.redis.scan_iter(pat):  # type: ignore[attr-defined]
                k = key.decode() if isinstance(key, bytes) else str(key)
                for p in prefixes:
                    path = k.split(":", 2)[-1]
                    if path.startswith(p):
                        app.state.redis.delete(key)
                        break
        except Exception:
            pass

    async def _maybe_cache_get(path: str, org: str, perform_request):
        if not app.state.redis or not _cacheable(path):
            return await perform_request()
        key = _cache_key(path, org)
        try:
            val = app.state.redis.get(key)
            if val:
                if _cache_hits is not None:
                    _cache_hits.labels(path).inc()  # type: ignore
                data = json.loads(val)
                return JSONResponse(status_code=data.get("status", 200), content=data.get("body", {}))
        except Exception:
            pass
        if _cache_misses is not None:
            _cache_misses.labels(path).inc()  # type: ignore
        resp = await perform_request()
        try:
            if getattr(resp, "status_code", 200) < 300:
                app.state.redis.setex(key, CACHE_TTL, json.dumps({"status": resp.status_code, "body": resp.body.decode() if hasattr(resp, 'body') else resp.body}))
        except Exception:
            pass
        return resp

    async def _idempotent_post(path: str, request: Request, perform_request):
        key = request.headers.get("Idempotency-Key", "").strip()
        if key:
            cached = await _get_idempotent_response(path, key)
            if cached:
                return cached
        resp = await perform_request()
        if key and getattr(resp, "status_code", 200) < 500:
            _store_idempotent_response(path, key, resp)
        return resp

    def _with_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
        trace_hdr = headers.get("traceparent") or _make_traceparent()
        out = dict(headers)
        out["traceparent"] = trace_hdr
        return out

    def _validate_response_schema(path: str, data: Any) -> None:
        _, resp_schema = _match_schema(path)
        if resp_schema:
            try:
                jsonschema_validate(instance=data, schema=resp_schema)
            except ValidationError as ve:
                if STRICT_RESPONSE_SCHEMA:
                    raise HTTPException(status_code=502, detail=f"response schema validation failed: {ve.message}")
                pass

    @app.middleware("http")
    async def auth_and_rate_limit(request: Request, call_next):
        token = request.headers.get("X-API-Key", "")
        if app.state.api_tokens and not _api_key_valid(token):
            return _error("UNAUTHORIZED", 401, "invalid api key")

        try:
            org_id = await _verify_jwt(request)
        except HTTPException as he:
            if he.status_code == 401:
                return _error("UNAUTHORIZED", 401, he.detail or "invalid token")
            if he.status_code == 403:
                return _error("FORBIDDEN", 403, he.detail or "forbidden")
            raise
        request.state.org_id = org_id

        client_ip = request.client.host if request.client else "unknown"
        key = _bucket_key(client_ip, org_id, request.url.path)
        limit = RL_RPS
        try:
            if app.state.redis:
                val = app.state.redis.incr(key)
                if val == 1:
                    app.state.redis.expire(key, 1)
                if val > limit:
                    return _error("RATE_LIMIT_EXCEEDED", 429, "rate limit exceeded")
            else:
                store = app.state.rate_store
                count = store.get(key, 0) + 1
                store[key] = count
                if count > limit:
                    return _error("RATE_LIMIT_EXCEEDED", 429, "rate limit exceeded")
        except Exception:
            pass

        if _is_mutating(request.method):
            _quota_inc(org_id)
            try:
                _quota_check(org_id)
            except HTTPException as he:
                return _error("QUOTA_EXCEEDED", he.status_code, he.detail or "quota exceeded")

        roles = _get_roles(request)
        try:
            _rbac_check(org_id, roles, request.method, request.url.path)
        except HTTPException as he:
            return _error("FORBIDDEN", he.status_code, he.detail or "forbidden")

        return await call_next(request)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"ok": True}

    @app.post("/cache/invalidate")
    async def cache_invalidate(request: Request) -> Dict[str, Any]:
        token = request.headers.get("X-API-Key", "")
        if app.state.api_tokens and not _api_key_valid(token):
            raise HTTPException(status_code=401, detail="invalid api key")
        body = await request.json()
        prefixes = body.get("prefixes") or []
        org = body.get("org")
        if not isinstance(prefixes, list) or not all(isinstance(p, str) for p in prefixes):
            raise HTTPException(status_code=400, detail="invalid prefixes")
        _invalidate_cache(prefixes, org)
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
                    data = json.loads(body or b"{}")
                    if not isinstance(data, dict):
                        raise HTTPException(status_code=422, detail="json body must be an object")
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(status_code=400, detail="invalid json")
            # Schema validation
            req_schema, _ = _match_schema(request.url.path)
            if req_schema and request.headers.get("content-type", "").startswith("application/json"):
                try:
                    jsonschema_validate(instance=json.loads(body or b"{}"), schema=req_schema)
                except ValidationError as ve:
                    raise HTTPException(status_code=422, detail=f"schema validation failed: {ve.message}")
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

    def _with_error_wrap(fn):
        async def inner(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except HTTPException as he:
                if he.status_code == 413:
                    return _error("PAYLOAD_TOO_LARGE", 413, he.detail or "payload too large")
                if he.status_code == 422:
                    return _error("SCHEMA_INVALID", 422, he.detail or "schema validation failed")
                if he.status_code == 503:
                    return _error("UPSTREAM_UNAVAILABLE", 503, he.detail or "upstream unavailable")
                if he.status_code == 400:
                    return _error("BAD_REQUEST", 400, he.detail or "bad request")
                raise
            except Exception:
                return _error("UPSTREAM_ERROR", 502, "upstream error")
        return inner

    def _cache_invalidate_after_mutation(path: str, org: str) -> None:
        if not CACHE_INVALIDATE_PREFIXES:
            return
        _invalidate_cache(CACHE_INVALIDATE_PREFIXES, org)

    @_with_error_wrap
    async def _proxy_do(target: str, request: Request, cb_target: str) -> JSONResponse:
        async with httpx.AsyncClient(timeout=20, **_mtls_args()) as client:
            body = await _validate_json_body(request)
            headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
            headers = _with_trace_headers(headers)
            try:
                resp = await client.request(request.method, target, content=body, headers=headers)
                _record_cb(cb_target, resp.status_code < 500)
            except Exception:
                _record_cb(cb_target, False)
                raise HTTPException(status_code=502, detail="upstream error")
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            _validate_response_schema(request.url.path, data if isinstance(data, dict) else {"data": data})
            out = JSONResponse(status_code=resp.status_code, content=data if isinstance(data, dict) else {"data": data})
            if _is_mutating(request.method):
                _cache_invalidate_after_mutation(request.url.path, getattr(request.state, "org_id", "default"))
            return out

    @app.api_route("/proxy/integrations/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_integrations(path: str, request: Request) -> Any:
        if not INTEGRATIONS_BASE_URL:
            return _error("UPSTREAM_NOT_CONFIGURED", 502, "integrations not configured")
        target = f"{INTEGRATIONS_BASE_URL}/{path}"
        if not is_allowed_host(target):
            return _error("OUTBOUND_DENIED", 403, "outbound host not allowed")
        _check_cb("integrations")

        org = getattr(request.state, "org_id", "default")

        async def _do():
            return await _proxy_do(target, request, "integrations")

        if request.method == "GET" and _cacheable(request.url.path):
            return await _maybe_cache_get(request.url.path, org, _do)
        if request.method == "POST":
            return await _idempotent_post(request.url.path, request, _do)
        return await _do()

    @app.api_route("/proxy/automation/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_automation(path: str, request: Request) -> Any:
        if not AUTOMATION_BASE_URL:
            return _error("UPSTREAM_NOT_CONFIGURED", 502, "automation not configured")
        target = f"{AUTOMATION_BASE_URL}/{path}"
        if not is_allowed_host(target):
            return _error("OUTBOUND_DENIED", 403, "outbound host not allowed")
        _check_cb("automation")

        async def _do():
            return await _proxy_do(target, request, "automation")

        if request.method == "GET" and _cacheable(request.url.path):
            org = getattr(request.state, "org_id", "default")
            return await _maybe_cache_get(request.url.path, org, _do)
        if request.method == "POST":
            return await _idempotent_post(request.url.path, request, _do)
        return await _do()

    return app


app = create_app()

