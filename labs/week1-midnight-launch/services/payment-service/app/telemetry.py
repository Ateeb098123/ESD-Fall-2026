"""Payment Prometheus instruments."""
from prometheus_client import Counter, Histogram
BUCKETS=[0.005,0.01,0.025,0.05,0.1,0.25,0.5,1.0,2.0,3.0,3.5,5.0,10.0]
REQUESTS=Counter("payment_requests_total","Total requests",["method","route","status"])
LATENCY=Histogram("payment_request_duration_seconds","Request duration",["method","route","status"],buckets=BUCKETS)
