"""Single-line ECS-friendly JSON logging for container collection."""

import json
import logging
from datetime import datetime, timezone
from .config import SERVICE_NAME

logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

def log_event(message: str, *, level: str = "INFO", **fields) -> None:
    payload = {"@timestamp": datetime.now(timezone.utc).isoformat(), "service": {"name": SERVICE_NAME}, "log": {"level": level.lower()}, "message": message, **fields}
    getattr(logger, level.lower(), logger.info)(json.dumps(payload, separators=(",", ":")))
