"""Thread-safe CLOSED/OPEN/HALF-OPEN state machine."""

import time
from .state import CB_LOCK, CHAOS_STATE, STATE_TO_GAUGE
from .telemetry import CIRCUIT_BREAKER_STATE

def publish_state() -> None:
    CIRCUIT_BREAKER_STATE.set(STATE_TO_GAUGE.get(CHAOS_STATE["circuit_breaker"], 0))

def allows_request() -> bool:
    if not CHAOS_STATE["circuit_breaker_enabled"]:
        return True
    with CB_LOCK:
        if CHAOS_STATE["circuit_breaker"] == "OPEN":
            opened_at = CHAOS_STATE["opened_at"]
            if opened_at is not None and time.time() - opened_at >= CHAOS_STATE["recovery_timeout_seconds"]:
                CHAOS_STATE.update(circuit_breaker="HALF-OPEN", half_open_successes=0)
                publish_state()
                return True
            publish_state()
            return False
        publish_state()
        return True

def record_success() -> None:
    if not CHAOS_STATE["circuit_breaker_enabled"]:
        return
    with CB_LOCK:
        if CHAOS_STATE["circuit_breaker"] == "HALF-OPEN":
            CHAOS_STATE["half_open_successes"] += 1
            if CHAOS_STATE["half_open_successes"] >= CHAOS_STATE["half_open_required"]:
                CHAOS_STATE.update(circuit_breaker="CLOSED", failure_count=0, opened_at=None)
        else:
            CHAOS_STATE.update(circuit_breaker="CLOSED", failure_count=0)
        publish_state()

def record_failure() -> None:
    if not CHAOS_STATE["circuit_breaker_enabled"]:
        return
    with CB_LOCK:
        if CHAOS_STATE["circuit_breaker"] == "HALF-OPEN":
            CHAOS_STATE.update(circuit_breaker="OPEN", opened_at=time.time())
        else:
            CHAOS_STATE["failure_count"] += 1
            if CHAOS_STATE["failure_count"] >= CHAOS_STATE["failure_threshold"]:
                CHAOS_STATE.update(circuit_breaker="OPEN", opened_at=time.time())
        publish_state()
