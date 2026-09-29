"""High-level browser search + read helpers for ANA_MAX OS-22."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Callable
from urllib.parse import quote_plus

from ANA_MAX.tools.web_scraper import web_scrape
from ANA_MAX.tools.windows_local_tools import open_url_in_windows_app


SEARCH_ENGINES: dict[str, str] = {
    "duckduckgo": "https://duckduckgo.com/html/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "google": "https://www.google.com/search?q={query}",
}


def _ascii_text(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii")


def build_search_url(query: str, engine: str = "bing") -> dict[str, Any]:
    clean_query = " ".join(str(query or "").strip().split())
    clean_engine = str(engine or "bing").strip().lower()
    template = SEARCH_ENGINES.get(clean_engine)
    if not clean_query:
        return {
            "schema": "ana.os22.browser_search_url.v1",
            "success": False,
            "error": "empty_query",
            "query": "",
            "engine": clean_engine,
            "url": "",
            "local_only": True,
            "metadata_only": True,
        }
    if template is None:
        clean_engine = "bing"
        template = SEARCH_ENGINES[clean_engine]
    return {
        "schema": "ana.os22.browser_search_url.v1",
        "success": True,
        "query": clean_query,
        "engine": clean_engine,
        "url": template.format(query=quote_plus(clean_query)),
        "local_only": True,
        "metadata_only": True,
    }


def summarize_search_text(text: str, max_chars: int = 700) -> str:
    compact = " ".join(_ascii_text(text).split())
    compact = re.sub(r"\s+", " ", compact).strip()
    if not compact:
        return ""
    limit = max(1, int(max_chars or 700))
    return compact[:limit].rstrip()


def browser_search_read(
    query: str,
    browser: str = "brave",
    engine: str = "bing",
    max_chars: int = 4000,
    timeout: int = 20,
    opener: Callable[[str, str], dict[str, Any]] | None = None,
    scraper: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    url_payload = build_search_url(query, engine=engine)
    if not url_payload.get("success"):
        return {
            "schema": "ana.os22.browser_search_read.v1",
            "success": False,
            "query": str(query or ""),
            "browser": str(browser or ""),
            "engine": str(engine or ""),
            "url": "",
            "open_result": {},
            "scrape_result": {},
            "text_preview": "",
            "summary": "",
            "error": url_payload.get("error", "search_url_error"),
            "local_only": True,
        }

    target_url = str(url_payload["url"])
    open_result = (opener or open_url_in_windows_app)(str(browser or "brave"), target_url)
    scrape_result = (scraper or web_scrape)(
        url=target_url,
        max_chars=max(500, int(max_chars or 4000)),
        timeout=max(5, int(timeout or 20)),
    )
    text_preview = summarize_search_text(str(scrape_result.get("text", "")), max_chars=max_chars)
    success = bool(open_result.get("success")) or bool(scrape_result.get("success"))
    error = ""
    if not success:
        error = str(open_result.get("error") or scrape_result.get("error") or "browser_search_read_failed")
    summary = text_preview[:700]
    return {
        "schema": "ana.os22.browser_search_read.v1",
        "success": success,
        "query": str(url_payload["query"]),
        "browser": str(browser or "brave"),
        "engine": str(url_payload["engine"]),
        "url": target_url,
        "open_result": open_result,
        "scrape_result": {
            "schema": scrape_result.get("schema", ""),
            "success": bool(scrape_result.get("success")),
            "status_code": scrape_result.get("status_code"),
            "content_type": scrape_result.get("content_type", ""),
            "text_length": scrape_result.get("text_length", 0),
            "truncated": bool(scrape_result.get("truncated", False)),
            "error": scrape_result.get("error", ""),
        },
        "text_preview": text_preview,
        "summary": summary,
        "error": error,
        "local_only": True,
    }


def dumps_result(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True, sort_keys=True)
