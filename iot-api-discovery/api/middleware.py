from __future__ import annotations

import time
import uuid
import json
from typing import Callable

from fastapi import Request


async def request_id_and_logging_middleware(request: Request, call_next: Callable):
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    start = time.time()
    # Attach request id to state
    request.state.request_id = rid
    # Propagate request id downstream
    request_headers = dict(request.headers)
    request_headers["X-Request-Id"] = rid
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    try:
        log = {
            "ts": int(start),
            "request_id": rid,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "client": getattr(request.client, "host", None),
            "headers": {"x_request_id": rid},
        }
        print(json.dumps(log))
    except Exception:
        pass
    response.headers["X-Request-Id"] = rid
    return response

