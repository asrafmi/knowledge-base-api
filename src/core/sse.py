import json
from typing import Any


def sse_event(data: dict[str, Any], event: str | None = None) -> str:
    payload = f"data: {json.dumps(data)}\n\n"
    if event:
        payload = f"event: {event}\n{payload}"
    return payload
