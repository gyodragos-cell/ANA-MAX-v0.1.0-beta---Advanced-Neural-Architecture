"""OS-22 web learning helper: scrape a URL and store useful text in RAG."""

from __future__ import annotations

import unicodedata
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

from ANA_MAX.tools.rag_store_text import rag_store_text
from ANA_MAX.tools.web_scraper import html_to_text
from ANA_MAX.tools.web_scraper import web_scrape


SCHEMA = "ana.os22.web_learn_url.v1"
COURSE_SCHEMA = "ana.os22.web_learn_course.v1"


def _ascii_text(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", errors="ignore").decode("ascii")


def _source_label(url: str, source_label: str) -> str:
    label = _ascii_text(source_label).strip()
    if label:
        return label[:180]
    return f"web_learning:{_ascii_text(url).strip()[:160]}"


def _summary(text: str, max_chars: int = 700) -> str:
    payload = " ".join(_ascii_text(text).split())
    payload = payload.replace("ny:-->", "").replace("-->", "")
    if len(payload) <= max_chars:
        return payload
    return payload[:max_chars].rsplit(" ", 1)[0].strip() + "..."


def _main_html_fragment(html: str) -> str:
    payload = str(html or "")
    match = re.search(r"<div[^>]+id=['\"]main['\"][^>]*>", payload, flags=re.IGNORECASE)
    if not match:
        return payload
    start = match.start()
    end_candidates = [
        index
        for token in ("id=\"right\"", "id='right'", "id=\"footer\"", "id='footer'")
        for index in [payload.find(token, match.end())]
        if index > start
    ]
    end = min(end_candidates) if end_candidates else len(payload)
    fragment = payload[start:end]
    return re.sub(r"<!--.*?-->", "", fragment, flags=re.DOTALL)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def _fetch_html(url: str, timeout: int) -> tuple[str, str, int]:
    request = Request(url, headers={"User-Agent": "ANA_MAX_OS22_CourseLearning/1.0"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        status_code = int(getattr(response, "status", 200) or 200)
    return text, content_type, status_code


def _normalize_url(url: str) -> str:
    target, _fragment = urldefrag(str(url or "").strip())
    return target.rstrip("/")


def _is_html_like(url: str) -> bool:
    path = urlparse(url).path.lower()
    blocked = (
        ".7z",
        ".avi",
        ".bin",
        ".css",
        ".exe",
        ".gif",
        ".gz",
        ".ico",
        ".jpg",
        ".jpeg",
        ".js",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".rar",
        ".svg",
        ".webp",
        ".zip",
    )
    return not any(path.endswith(ext) for ext in blocked)


def _course_path_prefix(start_url: str) -> str:
    path = urlparse(start_url).path or "/"
    if path.endswith("/"):
        return path.rstrip("/") or "/"
    if "." in Path(path).name:
        parent = str(Path(path).parent).replace("\\", "/")
        return parent.rstrip("/") or "/"
    return path.rstrip("/") or "/"


def _inside_path_prefix(candidate_url: str, path_prefix: str) -> bool:
    if not path_prefix or path_prefix == "/":
        return True
    path = urlparse(candidate_url).path or "/"
    return path == path_prefix or path.startswith(path_prefix + "/")


def _course_link_priority(url: str) -> int:
    path = urlparse(url).path.lower()
    name = Path(path).name.lower()
    if name == "default.asp":
        return 0
    lower_priority_prefixes = (
        "php_ref",
        "php_examples",
        "php_compiler",
        "php_quiz",
        "php_exercises",
        "php_practice",
        "php_server",
        "php_syllabus",
        "php_study",
    )
    if name.startswith("php_") and not name.startswith(lower_priority_prefixes):
        return 1
    if name.startswith("func_"):
        return 4
    return 3


def _extract_links(base_url: str, html: str, same_domain: bool, path_prefix: str = "") -> tuple[list[str], int, int]:
    parser = _LinkParser()
    parser.feed(str(html or ""))
    base = urlparse(base_url)
    join_base = base_url
    if base.path and not base.path.endswith("/") and "." not in Path(base.path).name:
        join_base = base_url + "/"
    links: list[str] = []
    skipped_external = 0
    skipped_out_of_scope = 0
    seen: set[str] = set()
    for raw_href in parser.links:
        href = str(raw_href or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        candidate = _normalize_url(urljoin(join_base, href))
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if same_domain and parsed.netloc.lower() != base.netloc.lower():
            skipped_external += 1
            continue
        if not _inside_path_prefix(candidate, path_prefix):
            skipped_out_of_scope += 1
            continue
        if not _is_html_like(candidate):
            continue
        if candidate not in seen:
            seen.add(candidate)
            links.append(candidate)
    ordered = sorted(enumerate(links), key=lambda item: (_course_link_priority(item[1]), item[0]))
    return [link for _index, link in ordered], skipped_external, skipped_out_of_scope


def web_learn_url(
    *,
    url: str,
    source_label: str = "",
    max_chars: int = 12000,
    chunk_size: int = 1200,
    chunk_overlap: int = 100,
    timeout: int = 30,
    scraper: Callable[..., dict[str, Any]] | None = None,
    store: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    target = _ascii_text(url).strip()
    source = _source_label(target, source_label)
    if not target:
        return {
            "schema": SCHEMA,
            "success": False,
            "local_only": True,
            "url": target,
            "source_label": source,
            "summary": "",
            "stored_count": 0,
            "memory_ids": [],
            "error": "missing_url",
        }

    scrape_result = (scraper or web_scrape)(
        url=target,
        max_chars=max_chars,
        timeout=timeout,
    )
    if not scrape_result.get("success"):
        return {
            "schema": SCHEMA,
            "success": False,
            "local_only": True,
            "url": target,
            "source_label": source,
            "summary": "",
            "stored_count": 0,
            "memory_ids": [],
            "scrape": scrape_result,
            "error": _ascii_text(scrape_result.get("error", "scrape_failed")),
        }

    text = _ascii_text(scrape_result.get("text", ""))
    if not text.strip():
        return {
            "schema": SCHEMA,
            "success": False,
            "local_only": True,
            "url": target,
            "source_label": source,
            "summary": "",
            "stored_count": 0,
            "memory_ids": [],
            "scrape": scrape_result,
            "error": "empty_scraped_text",
        }

    store_result = (store or rag_store_text)(
        text=text,
        source=source,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not store_result.get("success"):
        return {
            "schema": SCHEMA,
            "success": False,
            "local_only": True,
            "url": target,
            "source_label": source,
            "summary": _summary(text),
            "stored_count": 0,
            "memory_ids": [],
            "scrape": scrape_result,
            "store": store_result,
            "error": _ascii_text(store_result.get("error", "store_failed")),
        }

    memory_ids = [_ascii_text(item) for item in store_result.get("memory_ids", [])]
    return {
        "schema": SCHEMA,
        "success": True,
        "local_only": True,
        "url": target,
        "source_label": source,
        "text_length": len(text),
        "summary": _summary(text),
        "stored_count": int(store_result.get("stored_count", len(memory_ids)) or 0),
        "memory_ids": memory_ids,
        "scrape": {
            "schema": scrape_result.get("schema", ""),
            "success": scrape_result.get("success", False),
            "status_code": scrape_result.get("status_code", 0),
            "content_type": scrape_result.get("content_type", ""),
            "truncated": scrape_result.get("truncated", False),
        },
        "store": {
            "schema": store_result.get("schema", ""),
            "success": store_result.get("success", False),
            "stored_count": store_result.get("stored_count", 0),
        },
        "error": "",
    }


def web_learn_course(
    *,
    start_url: str,
    source_label: str = "",
    max_pages: int = 8,
    max_depth: int = 2,
    same_domain: bool = True,
    max_chars_per_page: int = 10000,
    chunk_size: int = 1200,
    chunk_overlap: int = 100,
    timeout: int = 30,
    fetcher: Callable[[str, int], tuple[str, str, int]] | None = None,
    store: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    start = _normalize_url(_ascii_text(start_url))
    source = _source_label(start, source_label).replace("web_learning:", "course_learning:")
    page_limit = max(1, min(int(max_pages or 8), 20))
    depth_limit = max(0, min(int(max_depth or 2), 5))
    chars_limit = max(1, min(int(max_chars_per_page or 10000), 50000))

    parsed_start = urlparse(start)
    if not start:
        return {
            "schema": COURSE_SCHEMA,
            "success": False,
            "local_only": True,
            "start_url": start,
            "source_label": source,
            "page_count": 0,
            "stored_count": 0,
            "memory_ids": [],
            "learned_urls": [],
            "skipped_external_count": 0,
            "truncated": False,
            "summary": "",
            "error": "missing_url",
        }
    if parsed_start.scheme not in {"http", "https"} or not parsed_start.netloc:
        return {
            "schema": COURSE_SCHEMA,
            "success": False,
            "local_only": True,
            "start_url": start,
            "source_label": source,
            "page_count": 0,
            "stored_count": 0,
            "memory_ids": [],
            "learned_urls": [],
            "skipped_external_count": 0,
            "truncated": False,
            "summary": "",
            "error": "unsupported_url",
        }

    fetch = fetcher or _fetch_html
    save = store or rag_store_text
    queue: list[tuple[str, int]] = [(start, 0)]
    visited: set[str] = set()
    learned_urls: list[str] = []
    failed_pages: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    memory_ids: list[str] = []
    summaries: list[str] = []
    skipped_external_count = 0
    skipped_out_of_scope_count = 0
    path_prefix = _course_path_prefix(start)

    while queue and len(learned_urls) < page_limit:
        url, depth = queue.pop(0)
        normalized = _normalize_url(url)
        if normalized in visited:
            continue
        visited.add(normalized)
        try:
            html, content_type, status_code = fetch(normalized, int(timeout or 30))
            text = html_to_text(_main_html_fragment(html), max_chars=chars_limit)
            text = text.replace("ny:-->", "").replace("-->", "")
            if not text.strip():
                failed_pages.append({"url": normalized, "error": "empty_text"})
                continue
            store_result = save(
                text=text,
                source=f"{source}:page:{len(learned_urls) + 1}",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            if not store_result.get("success"):
                failed_pages.append({"url": normalized, "error": _ascii_text(store_result.get("error", "store_failed"))})
                continue
            learned_urls.append(normalized)
            memory_ids.extend(_ascii_text(item) for item in store_result.get("memory_ids", []))
            page_summary = _summary(text, max_chars=220)
            summaries.append(page_summary)
            pages.append(
                {
                    "url": normalized,
                    "depth": depth,
                    "source": f"{source}:page:{len(learned_urls)}",
                    "text_length": len(text),
                    "stored_count": int(store_result.get("stored_count", 0) or 0),
                    "summary": page_summary,
                    "status_code": int(status_code or 0),
                    "content_type": _ascii_text(content_type),
                }
            )
            if depth < depth_limit and len(learned_urls) < page_limit:
                links, skipped, skipped_scope = _extract_links(
                    normalized,
                    html,
                    same_domain=bool(same_domain),
                    path_prefix=path_prefix,
                )
                skipped_external_count += skipped
                skipped_out_of_scope_count += skipped_scope
                for link in links:
                    if link not in visited and all(link != queued_url for queued_url, _depth in queue):
                        queue.append((link, depth + 1))
        except Exception as exc:
            failed_pages.append({"url": normalized, "error": _ascii_text(exc)})

    total_stored = len(memory_ids)
    return {
        "schema": COURSE_SCHEMA,
        "success": bool(learned_urls),
        "local_only": True,
        "start_url": start,
        "source_label": source,
        "same_domain": bool(same_domain),
        "max_pages": page_limit,
        "max_depth": depth_limit,
        "page_count": len(learned_urls),
        "stored_count": total_stored,
        "memory_ids": memory_ids,
        "learned_urls": learned_urls,
        "pages": pages,
        "failed_pages": failed_pages,
        "failed_count": len(failed_pages),
        "skipped_external_count": skipped_external_count,
        "skipped_out_of_scope_count": skipped_out_of_scope_count,
        "path_prefix": path_prefix,
        "truncated": bool(queue) or len(learned_urls) >= page_limit,
        "summary": _summary(" ".join(summaries), max_chars=900),
        "error": "" if learned_urls else "no_pages_learned",
    }
