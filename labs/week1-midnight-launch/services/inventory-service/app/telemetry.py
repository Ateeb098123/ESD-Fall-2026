"""Inventory Prometheus instruments."""
from prometheus_client import Counter, Gauge, Histogram

BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 3.5, 5.0, 10.0]
REQUESTS = Counter("inventory_requests_total", "Total requests", ["method", "route", "status"])
LATENCY = Histogram("inventory_request_duration_seconds", "Request duration", ["method", "route", "status"], buckets=BUCKETS)
DB_LOCK_WAITERS = Gauge("postgres_connection_pool_waiters", "DB connection-pool waiters")
