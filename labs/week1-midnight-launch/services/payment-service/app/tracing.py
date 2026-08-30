"""W3C parent/child trace-context handling."""
import random
from fastapi import Request
def child_span(request: Request)->dict:
    incoming=request.headers.get("traceparent"); span_id=f"{random.getrandbits(64):016x}"
    if incoming and incoming.count("-")==3: _,trace_id,parent_span_id,flags=incoming.split("-")
    else: trace_id,parent_span_id,flags=f"{random.getrandbits(128):032x}",None,"01"
    return {"trace_id":trace_id,"span_id":span_id,"parent_span_id":parent_span_id,"traceparent":f"00-{trace_id}-{span_id}-{flags}"}
