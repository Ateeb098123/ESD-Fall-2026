"""Business and chaos-control HTTP routes."""

import time
from fastapi import APIRouter, HTTPException, Request

from .circuit_breaker import allows_request, publish_state, record_failure, record_success
from .clients import FANOUT_EXECUTOR, fanout_leg, request_downstream, reset_downstreams
from .state import BASE_SERIES_COUNT, CARDINALITY_LOCK, CARDINALITY_SEEN_USERS, CB_LOCK, CHAOS_STATE, STATE_TO_GAUGE
from .structured_logging import log_event
from .telemetry import CARDINALITY_BOMB, CARDINALITY_SERIES, FANOUT_DEPENDENCIES, FANOUT_REQUESTS, FANOUT_SLOW
from .tracing import root_context

router = APIRouter()

@router.post("/checkout")
def checkout(request: Request):
    context = root_context()
    request.state.trace_id = context["trace_id"]
    headers = {"traceparent": context["traceparent"]}
    if not allows_request():
        log_event("circuit breaker rejected checkout", level="WARNING", trace={"id": context["trace_id"]}, circuit_breaker={"state": "OPEN"})
        raise HTTPException(503, "[Circuit Breaker OPEN] Gateway fail-fast active to protect backend!")
    try:
        inventory = request_downstream("inventory", "GET", "/inventory/reserve", headers)
        if inventory.status_code != 200:
            raise HTTPException(inventory.status_code, f"[Inventory Service Failure] {inventory.text}")
        payment = request_downstream("payment", "POST", "/payment/charge", headers)
        if payment.status_code != 200:
            raise HTTPException(payment.status_code, f"[Payment Service Failure] {payment.text}")
        fanout_report = None
        n = CHAOS_STATE["fanout_n"]
        if n:
            FANOUT_REQUESTS.inc()
            futures = [FANOUT_EXECUTOR.submit(fanout_leg, headers) for _ in range(n)]
            slow_legs = sum(1 for future in futures if future.result())
            if slow_legs:
                FANOUT_SLOW.inc()
            fanout_report = {"dependencies": n, "slow_legs": slow_legs}
        record_success()
        return {"status": "success", "message": "Ticket purchased successfully!", "trace_id": context["trace_id"], "traceparent": context["traceparent"], "gateway_span_id": context["span_id"], "inventory": inventory.json(), "payment": payment.json(), "fanout": fanout_report}
    except HTTPException:
        record_failure()
        raise
    except Exception as exc:
        record_failure()
        raise HTTPException(500, f"Checkout failed downstream: {exc}") from exc

@router.get("/chaos/status")
def chaos_status():
    return CHAOS_STATE

@router.post("/chaos/cardinality")
def toggle_cardinality(active: bool):
    CHAOS_STATE["cardinality_bomb"] = active
    if not active:
        with CARDINALITY_LOCK:
            CARDINALITY_SEEN_USERS.clear()
            CHAOS_STATE["cardinality_users_count"] = 0
        CARDINALITY_BOMB.clear()
        CARDINALITY_SERIES.set(BASE_SERIES_COUNT)
    return {"status": "ok", "cardinality_bomb": active}

@router.post("/chaos/circuit-breaker")
def toggle_circuit_breaker(enabled: bool, state: str = "CLOSED"):
    state = state.upper()
    if state not in STATE_TO_GAUGE:
        raise HTTPException(400, f"Invalid state '{state}'. Use CLOSED, OPEN or HALF-OPEN.")
    with CB_LOCK:
        CHAOS_STATE.update(circuit_breaker_enabled=enabled, circuit_breaker=state, failure_count=0, half_open_successes=0, opened_at=time.time() if state == "OPEN" else None)
        publish_state()
    return {"status": "ok", "circuit_breaker_enabled": enabled, "state": state}

@router.post("/chaos/fanout")
def set_fanout(n: int):
    if not 0 <= n <= 100:
        raise HTTPException(400, "n must be between 0 and 100")
    CHAOS_STATE["fanout_n"] = n
    FANOUT_DEPENDENCIES.set(n)
    return {"status": "ok", "fanout_n": n}

@router.post("/chaos/reset")
def reset_chaos():
    CHAOS_STATE.update(cardinality_bomb=False, fanout_n=0)
    with CB_LOCK:
        CHAOS_STATE.update(circuit_breaker_enabled=False, circuit_breaker="CLOSED", failure_count=0, half_open_successes=0, opened_at=None)
        publish_state()
    with CARDINALITY_LOCK:
        CARDINALITY_SEEN_USERS.clear()
        CHAOS_STATE["cardinality_users_count"] = 0
    CARDINALITY_BOMB.clear()
    CARDINALITY_SERIES.set(BASE_SERIES_COUNT)
    FANOUT_DEPENDENCIES.set(0)
    reset_downstreams()
    return {"status": "ok", "message": "All chaos injections cleared"}

CARDINALITY_SERIES.set(BASE_SERIES_COUNT)
FANOUT_DEPENDENCIES.set(0)
publish_state()
