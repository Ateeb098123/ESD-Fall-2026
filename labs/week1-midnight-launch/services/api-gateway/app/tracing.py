"""Minimal W3C Trace Context helpers."""

import random

def new_span_id() -> str:
    return f"{random.getrandbits(64):016x}"

def root_context() -> dict[str, str]:
    trace_id = f"{random.getrandbits(128):032x}"
    span_id = new_span_id()
    return {"trace_id": trace_id, "span_id": span_id, "traceparent": f"00-{trace_id}-{span_id}-01"}

def trace_id_from_header(value: str | None) -> str | None:
    return value.split("-")[1] if value and value.count("-") == 3 else None
