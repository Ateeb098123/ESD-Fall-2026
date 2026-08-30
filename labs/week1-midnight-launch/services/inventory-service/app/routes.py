"""Inventory business and chaos routes."""
import random, time
from fastapi import APIRouter, HTTPException, Request
from .state import CHAOS_STATE
from .telemetry import DB_LOCK_WAITERS
from .tracing import child_span

router = APIRouter()

@router.get("/inventory/reserve")
def reserve_ticket(request: Request):
    span = child_span(request); request.state.trace_id = span["trace_id"]
    if CHAOS_STATE["db_locked"]:
        DB_LOCK_WAITERS.inc()
        try: time.sleep(CHAOS_STATE["lock_delay_seconds"])
        finally: DB_LOCK_WAITERS.dec()
        if random.random() < 0.15:
            raise HTTPException(504, "Postgres Query Lock Timeout (Deadlock)")
        return {"status": "reserved", "ticket_id": f"tkt_{random.randint(1000, 9999)}", "db_mode": "LOCKED_CACHE_MISS", "delay_ms": int(CHAOS_STATE["lock_delay_seconds"] * 1000), **span}
    time.sleep(random.uniform(0.005, 0.025))
    return {"status": "reserved", "ticket_id": f"tkt_{random.randint(1000, 9999)}", "db_mode": "NORMAL_CACHE_HIT", "delay_ms": 15, **span}

@router.get("/dependency/call")
def dependency_call(request: Request):
    span = child_span(request); request.state.trace_id = span["trace_id"]
    slow = random.random() < CHAOS_STATE["tail_probability"]
    time.sleep(CHAOS_STATE["tail_delay_seconds"] if slow else random.uniform(0.002, 0.008))
    return {"slow": slow, **span}

@router.get("/chaos/status")
def chaos_status(): return CHAOS_STATE

@router.post("/chaos/db-lock")
def toggle_db_lock(locked: bool, delay: float = 3.0):
    CHAOS_STATE.update(db_locked=locked, lock_delay_seconds=delay)
    if not locked: DB_LOCK_WAITERS.set(0)
    return {"status": "ok", "db_locked": locked, "delay_seconds": delay}

@router.post("/chaos/tail")
def set_tail(probability: float = 0.01, delay: float = 1.0):
    if not 0 <= probability <= 1: raise HTTPException(400, "probability must be between 0.0 and 1.0")
    CHAOS_STATE.update(tail_probability=probability, tail_delay_seconds=delay)
    return {"status": "ok", "tail_probability": probability, "tail_delay_seconds": delay}

@router.post("/chaos/reset")
def reset_chaos():
    CHAOS_STATE.update(db_locked=False, lock_delay_seconds=3.0, tail_probability=0.01, tail_delay_seconds=1.0)
    DB_LOCK_WAITERS.set(0)
    return {"status": "ok"}
