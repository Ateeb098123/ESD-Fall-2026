"""Payment business and chaos routes."""
import random,time
from fastapi import APIRouter,HTTPException,Request
from .state import CHAOS_STATE
from .tracing import child_span
router=APIRouter()
@router.post("/payment/charge")
def charge(request:Request):
    span=child_span(request); request.state.trace_id=span["trace_id"]
    time.sleep(random.uniform(0.02,0.06))
    if CHAOS_STATE["rate_limit_active"] and random.random()<CHAOS_STATE["error_rate_pct"]:
        raise HTTPException(429,"[Third-Party Payment API Rate Limited] 429 Too Many Requests — Retry-After: 60")
    return {"status":"charged","transaction_id":f"txn_{random.getrandbits(32):08x}",**span}
@router.get("/chaos/status")
def chaos_status(): return CHAOS_STATE
@router.post("/chaos/rate-limit")
def toggle_rate_limit(active:bool,error_rate:float=0.40):
    if not 0<=error_rate<=1: raise HTTPException(400,"error_rate must be between 0.0 and 1.0")
    CHAOS_STATE.update(rate_limit_active=active,error_rate_pct=error_rate)
    return {"status":"ok",**CHAOS_STATE}
@router.post("/chaos/reset")
def reset():
    CHAOS_STATE.update(rate_limit_active=False,error_rate_pct=0.40)
    return {"status":"ok"}
