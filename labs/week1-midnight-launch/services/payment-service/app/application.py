"""Payment FastAPI composition root."""
import time
from fastapi import FastAPI,Request,Response
from prometheus_client import CONTENT_TYPE_LATEST,generate_latest
from .routes import router
from .structured_logging import log_event
from .telemetry import LATENCY,REQUESTS
app=FastAPI(title="Payment Service")
@app.middleware("http")
async def observe(request:Request,call_next):
    path=request.url.path
    if path in ("/metrics","/health") or path.startswith("/chaos"): return await call_next(request)
    start=time.perf_counter(); status=500
    try:
        response=await call_next(request); status=response.status_code; return response
    finally:
        duration=time.perf_counter()-start
        REQUESTS.labels(request.method,path,str(status)).inc(); LATENCY.labels(request.method,path,str(status)).observe(duration)
        trace_id=getattr(request.state,"trace_id",None)
        log_event("request completed",level="ERROR" if status>=500 else "INFO",trace={"id":trace_id} if trace_id else {},http={"request":{"method":request.method},"response":{"status_code":status}},url={"path":path},event={"duration":int(duration*1_000_000_000)})
@app.get("/health")
def health(): return {"status":"ok","service":"payment-service"}
@app.get("/metrics")
def metrics(): return Response(content=generate_latest(),media_type=CONTENT_TYPE_LATEST)
app.include_router(router)
