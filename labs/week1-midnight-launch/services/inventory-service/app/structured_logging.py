"""ECS-friendly JSON logs."""
import json, logging
from datetime import datetime, timezone

logger = logging.getLogger("inventory-service")
logger.setLevel(logging.INFO); logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler(); handler.setFormatter(logging.Formatter("%(message)s")); logger.addHandler(handler)

def log_event(message: str, *, level: str = "INFO", **fields):
    payload = {"@timestamp": datetime.now(timezone.utc).isoformat(), "service": {"name": "inventory-service"}, "log": {"level": level.lower()}, "message": message, **fields}
    getattr(logger, level.lower(), logger.info)(json.dumps(payload, separators=(",", ":")))
