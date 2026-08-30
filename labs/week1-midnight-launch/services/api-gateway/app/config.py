"""Runtime configuration."""

import os

SERVICE_NAME = "api-gateway"
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8081")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8082")
REQUEST_TIMEOUT_SECONDS = 12.0
LATENCY_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 3.5, 5.0, 10.0]
