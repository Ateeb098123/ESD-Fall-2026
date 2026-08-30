"""Prometheus instruments for inbound, outbound, and chaos behavior."""

from prometheus_client import Counter, Gauge, Histogram
from .config import LATENCY_BUCKETS

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "route", "status"], buckets=LATENCY_BUCKETS)
ACTIVE_WORKERS = Gauge("gateway_active_workers", "Active request workers")
CIRCUIT_BREAKER_STATE = Gauge("circuit_breaker_state", "Circuit breaker state: 0 closed, 1 open, 2 half-open")
CARDINALITY_SERIES = Gauge("tsdb_cardinality_series_count", "Active series in cardinality exercise")
FANOUT_REQUESTS = Counter("gateway_fanout_requests_total", "Checkouts performing fan-out")
FANOUT_SLOW = Counter("gateway_fanout_slow_total", "Fan-outs with at least one slow leg")
FANOUT_DEPENDENCIES = Gauge("gateway_fanout_dependencies", "Configured fan-out width N")
CARDINALITY_BOMB = Counter("http_requests_user_tagged_total", "Unsafe per-user request metric", ["route", "user_id"])
OUTBOUND_REQUESTS = Counter("http_client_requests_total", "Downstream HTTP requests", ["dependency", "method", "route", "status"])
OUTBOUND_LATENCY = Histogram("http_client_request_duration_seconds", "Downstream request duration", ["dependency", "method", "route", "status"], buckets=LATENCY_BUCKETS)
