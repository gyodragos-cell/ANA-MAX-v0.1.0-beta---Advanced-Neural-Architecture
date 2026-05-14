from __future__ import annotations

from typing import List


def read_nonempty_lines(path: str, encoding: str = "utf-8") -> List[str]:
    with open(path, "r", encoding=encoding) as handle:
        return [line.strip() for line in handle if line.strip()]


def is_online(timeout: float = 1.5) -> bool:
    import requests

    try:
        requests.get("https://1.1.1.1", timeout=timeout)
        return True
    except Exception:
        return False
