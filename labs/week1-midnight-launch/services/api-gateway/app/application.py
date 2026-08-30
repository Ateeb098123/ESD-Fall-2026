"""FastAPI composition root and request telemetry middleware."""

import random
import time
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .routes import router
from .state import BASE_SERIES_COUNT, CARDINALITY_LOCK, CARDINALITY_SEEN_USERS, CHAOS_STATE
from .structured_logging import log_event
from .telemetry import ACTIVE_WORKERS, CARDINALITY_BOMB, CARDINALITY_SERIES, LATENCY, REQUEST_COUNT
from .tracing import trace_id_from_header

app = FastAPI(title="API Gateway Service")

@app.middleware("http")
async def observe_request(request: Request, call_next):
    path = request.url.path
    if path in ("/metrics", "/health") or path.startswith("/chaos"):
        return await call_next(request)
    ACTIVE_WORKERS.inc()
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        ACTIVE_WORKERS.dec()
        REQUEST_COUNT.labels(request.method, path, str(status)).inc()
        LATENCY.labels(request.method, path, str(status)).observe(duration)
        if CHAOS_STATE["cardinality_bomb"]:
            user_id = f"usr_{random.randint(1, 100000)}"
            CARDINALITY_BOMB.labels(path, user_id).inc()
            with CARDINALITY_LOCK:
                CARDINALITY_SEEN_USERS.add(user_id)
                CHAOS_STATE["cardinality_users_count"] = len(CARDINALITY_SEEN_USERS)
                CARDINALITY_SERIES.set(BASE_SERIES_COUNT + len(CARDINALITY_SEEN_USERS))
        trace_id = getattr(request.state, "trace_id", None) or trace_id_from_header(request.headers.get("traceparent"))
        log_event("request completed", level="ERROR" if status >= 500 else "INFO", trace={"id": trace_id} if trace_id else {}, http={"request": {"method": request.method}, "response": {"status_code": status}}, url={"path": path}, event={"duration": int(duration * 1_000_000_000)})

@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(router)
