from __future__ import annotations

import json
from typing import Any, Mapping


def format_log_entry(entry: Mapping[str, Any]) -> str:
    return json.dumps(entry, ensure_ascii=False, sort_keys=True)
