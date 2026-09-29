from __future__ import annotations

import uuid


def generate_trace_id(prefix: str = "trace") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
