from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ana.core.error_model.errors import RoutingFailure, ValidationError


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    body: Mapping[str, Any]


class FakeHTTPService:
    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], HTTPResponse] = {}

    def register(self, method: str, url: str, response: HTTPResponse) -> None:
        self._responses[(method.upper(), url)] = response

    def request(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        method = str(payload.get("method", "GET")).upper()
        url = payload.get("url")
        if not isinstance(url, str) or not url:
            raise ValidationError("url is required", source="http")
        response = self._responses.get((method, url))
        if response is None:
            raise RoutingFailure(
                "no deterministic http response registered",
                source="http",
                details={"method": method, "url": url},
            )
        return {"status": response.status, "body": dict(response.body)}
