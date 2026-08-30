"""Mutable classroom fault state and synchronization primitives."""

import threading

BASE_SERIES_COUNT = 12
STATE_TO_GAUGE = {"CLOSED": 0, "OPEN": 1, "HALF-OPEN": 2}
CHAOS_STATE = {
    "cardinality_bomb": False, "circuit_breaker": "CLOSED",
    "circuit_breaker_enabled": False, "failure_count": 0,
    "failure_threshold": 5, "cardinality_users_count": 0,
    "recovery_timeout_seconds": 10.0, "half_open_required": 2,
    "half_open_successes": 0, "opened_at": None, "fanout_n": 0,
}
CB_LOCK = threading.Lock()
CARDINALITY_LOCK = threading.Lock()
CARDINALITY_SEEN_USERS: set[str] = set()
