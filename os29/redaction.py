from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(
    r"(?:^|[_-])(authorization|proxy.authorization|cookie|set.cookie|password|passwd|pwd|"
    r"token|access.token|refresh.token|api.key|apikey|client.secret|secret|private.key|"
    r"session|credential)(?:$|[_-])",
    re.IGNORECASE,
)
_SECRET_TEXT_PATTERNS = [
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)(password|passwd|pwd|access_token|refresh_token|api[_-]?key|client_secret|secret|token)=([^&\s]+)"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
]
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)


def redact_text(text: str, max_length: int = 2000) -> tuple[str, int]:
    if not isinstance(text, str):
        text = str(text)
    count = 0
    text, n = _PRIVATE_KEY.subn(REDACTED, text)
    count += n
    text, n = _SECRET_TEXT_PATTERNS[0].subn("Bearer " + REDACTED, text)
    count += n
    text, n = _SECRET_TEXT_PATTERNS[1].subn(lambda m: f"{m.group(1)}={REDACTED}", text)
    count += n
    text, n = _SECRET_TEXT_PATTERNS[2].subn(REDACTED, text)
    count += n
    if len(text) > max_length:
        text = text[:max_length] + f"…[TRUNCATED original_length={len(text)}]"
    return text, count


def is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9_-]", "", str(key).lower())
    return bool(_SECRET_KEY.search(normalized)) or any(
        word in normalized for word in ("authorization", "cookie", "password", "secret", "token", "apikey", "credential", "privatekey")
    )


def redact_value(value: Any, *, max_length: int = 2000, key_hint: str = "") -> tuple[Any, int]:
    if key_hint and is_sensitive_key(key_hint):
        return REDACTED, 1
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        total = 0
        for key, child in value.items():
            clean, count = redact_value(child, max_length=max_length, key_hint=str(key))
            result[str(key)] = clean
            total += count
        return result, total
    if isinstance(value, (list, tuple)):
        result = []
        total = 0
        for child in value:
            clean, count = redact_value(child, max_length=max_length)
            result.append(clean)
            total += count
        return result, total
    if isinstance(value, str):
        return redact_text(value, max_length=max_length)
    if value is None or isinstance(value, (bool, int, float)):
        return value, 0
    return redact_text(str(value), max_length=max_length)


def sanitize_url(url: str, *, max_length: int = 2000) -> tuple[str, int]:
    """Return a URL with user-info removed and secret query values redacted."""
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return "[INVALID_URL]", 1
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return "[INVALID_URL]", 1
    host = parsed.hostname.lower()
    try:
        port = parsed.port
    except ValueError:
        return "[INVALID_URL]", 1
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc = f"{netloc}:{port}"
    query = []
    redactions = 0
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if is_sensitive_key(key):
            query.append((key, REDACTED))
            redactions += 1
        else:
            clean, count = redact_text(value, max_length=max_length)
            query.append((key, clean))
            redactions += count
    path, n = redact_text(parsed.path, max_length=max_length)
    redactions += n
    result = urlunsplit((parsed.scheme.lower(), netloc, path, urlencode(query), ""))
    clean, n = redact_text(result, max_length=max_length)
    return clean, redactions + n