"""Instrumented downstream HTTP client calls."""

import time
from concurrent.futures import ThreadPoolExecutor
import requests
from .config import INVENTORY_SERVICE_URL, PAYMENT_SERVICE_URL, REQUEST_TIMEOUT_SECONDS
from .telemetry import OUTBOUND_LATENCY, OUTBOUND_REQUESTS

FANOUT_EXECUTOR = ThreadPoolExecutor(max_workers=128, thread_name_prefix="fanout")

def request_downstream(dependency: str, method: str, route: str, headers: dict[str, str]):
    base_url = INVENTORY_SERVICE_URL if dependency == "inventory" else PAYMENT_SERVICE_URL
    start = time.perf_counter()
    status = "transport_error"
    try:
        response = requests.request(method, f"{base_url}{route}", headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        status = str(response.status_code)
        return response
    finally:
        OUTBOUND_REQUESTS.labels(dependency, method, route, status).inc()
        OUTBOUND_LATENCY.labels(dependency, method, route, status).observe(time.perf_counter() - start)

def fanout_leg(headers: dict[str, str]) -> bool:
    try:
        return bool(request_downstream("inventory", "GET", "/dependency/call", headers).json().get("slow", False))
    except Exception:
        return True

def reset_downstreams() -> None:
    # Control-plane reset calls must not pollute the outgoing RED panels.
    for base_url in (INVENTORY_SERVICE_URL, PAYMENT_SERVICE_URL):
        try:
            requests.post(f"{base_url}/chaos/reset", timeout=3.0)
        except Exception:
            pass
