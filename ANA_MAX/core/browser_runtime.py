"""
Local hybrid browser runtime for ANA tools.

The runtime is intentionally optional and additive: Playwright enables live
automation when available, while HTTP/system-browser fallbacks keep imports and
read-only inspection usable for local agents without extra setup.
"""

from __future__ import annotations

import base64
import html
import json
import logging
import re
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except Exception:  # pragma: no cover - optional dependency
    PlaywrightError = Exception
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)


class BrowserRuntimeError(RuntimeError):
    """Raised when a requested browser action cannot be completed safely."""


_RUNTIME: BrowserRuntime | None = None


def get_browser_runtime() -> "BrowserRuntime":
    """Return the process-local browser runtime singleton."""
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = BrowserRuntime()
    return _RUNTIME


class BrowserRuntime:
    """Small Playwright-backed browser runtime with bounded local fallbacks."""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._history: list[dict[str, Any]] = []
        self._network_log: list[dict[str, Any]] = []
        self._route_handlers: dict[str, Any] = {}

    def open(self, url: str, visible: bool = True, new_session: bool = False, wait_seconds: int = 3) -> dict[str, Any]:
        if not HAS_PLAYWRIGHT:
            opened = webbrowser.open(url)
            self._record("open", {"url": url, "engine": "system_browser", "opened": bool(opened)})
            return {"url": url, "engine": "system_browser", "opened": bool(opened), "automation_ready": False}

        try:
            page = self._ensure_page(visible=visible, new_session=new_session)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._wait(wait_seconds)
            data = self._page_state(engine="playwright")
            self._record("open", data)
            return data
        except Exception as exc:
            raise BrowserRuntimeError(f"Playwright browser open failed: {exc}") from exc

    def navigate(self, url: str, wait_seconds: int = 3) -> dict[str, Any]:
        page = self._require_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self._wait(wait_seconds)
        data = self._page_state(engine="playwright")
        self._record("navigate", data)
        return data

    def inspect(
        self,
        url: str = "",
        selector: str = "body",
        wait_seconds: int = 3,
        screenshot_path: str = "",
    ) -> dict[str, Any]:
        if url and HAS_PLAYWRIGHT:
            try:
                self.open(url, visible=False, new_session=True, wait_seconds=wait_seconds)
                data = self.page_snapshot(selector=selector, limit=40)
                if screenshot_path:
                    data["screenshot"] = self.screenshot(screenshot_path=screenshot_path)
                data["engine"] = "playwright"
                self._record("inspect", {"url": data.get("url"), "engine": "playwright"})
                return data
            except Exception as exc:
                logger.debug("Playwright inspect fallback for %s: %s", url, exc)

        if url:
            data = self._http_inspect(url)
            self._record("inspect", {"url": url, "engine": "http"})
            return data

        return self.page_snapshot(selector=selector, limit=40)

    def read(self, selector: str = "body") -> dict[str, Any]:
        page = self._require_page()
        text = page.locator(selector).inner_text(timeout=5000)
        data = {
            "url": page.url,
            "title": page.title(),
            "selector": selector,
            "text_preview": self._compact_text(text),
            "text_length": len(text),
            "engine": "playwright",
        }
        self._record("read", {"selector": selector, "text_length": len(text)})
        return data

    def page_snapshot(self, selector: str = "body", limit: int = 40) -> dict[str, Any]:
        page = self._require_page()
        text = ""
        try:
            text = page.locator(selector).inner_text(timeout=5000)
        except Exception:
            text = page.locator("body").inner_text(timeout=5000)
        refs = self.dom_refs(limit=limit)
        return {
            "url": page.url,
            "title": page.title(),
            "selector": selector,
            "text_preview": self._compact_text(text),
            "text_length": len(text),
            "dom_refs": refs.get("refs", []),
            "dom_ref_count": refs.get("count", 0),
            "engine": "playwright",
        }

    def dom_refs(self, limit: int = 40) -> dict[str, Any]:
        page = self._require_page()
        safe_limit = max(1, min(int(limit or 40), 120))
        refs = page.evaluate(_DOM_REFS_SCRIPT, safe_limit)
        data = {"url": page.url, "title": page.title(), "count": len(refs), "refs": refs, "engine": "playwright"}
        self._record("dom_refs", {"count": len(refs)})
        return data

    def click(self, selector: str, wait_seconds: int = 1) -> dict[str, Any]:
        page = self._require_page()
        page.locator(selector).click(timeout=10000)
        self._wait(wait_seconds)
        data = self._page_state(engine="playwright") | {"selector": selector}
        self._record("click", data)
        return data

    def type(self, selector: str, text: str, wait_seconds: int = 1) -> dict[str, Any]:
        page = self._require_page()
        page.locator(selector).fill(text, timeout=10000)
        self._wait(wait_seconds)
        data = self._page_state(engine="playwright") | {"selector": selector, "text_length": len(text)}
        self._record("type", data)
        return data

    def press(self, selector: str, key: str = "Enter", wait_seconds: int = 1) -> dict[str, Any]:
        page = self._require_page()
        page.locator(selector).press(key, timeout=10000)
        self._wait(wait_seconds)
        data = self._page_state(engine="playwright") | {"selector": selector, "key": key}
        self._record("press", data)
        return data

    def screenshot(self, screenshot_path: str = "") -> dict[str, Any]:
        page = self._require_page()
        target = self._resolve_screenshot_path(screenshot_path)
        page.screenshot(path=str(target), full_page=True)
        data = {"path": str(target), "url": page.url, "title": page.title(), "engine": "playwright"}
        self._record("screenshot", data)
        return data

    def screenshot_base64(self, selector: str = "") -> dict[str, Any]:
        page = self._require_page()
        target = page.locator(selector) if selector else page
        image_bytes = target.screenshot()
        data = {
            "url": page.url,
            "title": page.title(),
            "base64": base64.b64encode(image_bytes).decode("ascii"),
            "bytes": len(image_bytes),
            "engine": "playwright",
        }
        self._record("screenshot_base64", {"bytes": len(image_bytes)})
        return data

    def evaluate(self, script: str) -> dict[str, Any]:
        result = self._require_page().evaluate(script)
        return {"result": result, "engine": "playwright"}

    def evaluate_on_selector(self, selector: str, script: str) -> dict[str, Any]:
        result = self._require_page().locator(selector).evaluate(script)
        return {"selector": selector, "result": result, "engine": "playwright"}

    def scroll(self, selector: str = "body", direction: str = "down", amount: int = 500) -> dict[str, Any]:
        page = self._require_page()
        direction = (direction or "down").lower()
        if direction == "top":
            page.evaluate("window.scrollTo(0, 0)")
        elif direction == "bottom":
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        else:
            delta = -abs(amount) if direction == "up" else abs(amount)
            page.evaluate("(delta) => window.scrollBy(0, delta)", delta)
        data = self._page_state(engine="playwright") | {"selector": selector, "direction": direction, "amount": amount}
        self._record("scroll", data)
        return data

    def hover(self, selector: str) -> dict[str, Any]:
        self._require_page().locator(selector).hover(timeout=10000)
        data = {"selector": selector, "engine": "playwright"}
        self._record("hover", data)
        return data

    def select_option(self, selector: str, value: str) -> dict[str, Any]:
        selected = self._require_page().locator(selector).select_option(value, timeout=10000)
        data = {"selector": selector, "selected": selected, "engine": "playwright"}
        self._record("select_option", data)
        return data

    def upload_file(self, selector: str, file_path: str) -> dict[str, Any]:
        target = Path(file_path).expanduser().resolve()
        if not target.exists():
            raise BrowserRuntimeError(f"Upload file not found: {target}")
        self._require_page().locator(selector).set_input_files(str(target), timeout=10000)
        data = {"selector": selector, "file_path": str(target), "engine": "playwright"}
        self._record("upload_file", data)
        return data

    def get_attribute(self, selector: str, attribute: str) -> dict[str, Any]:
        value = self._require_page().locator(selector).get_attribute(attribute, timeout=10000)
        return {"selector": selector, "attribute": attribute, "value": value, "engine": "playwright"}

    def wait_for_selector(self, selector: str, timeout_ms: int = 10000) -> dict[str, Any]:
        self._require_page().locator(selector).wait_for(timeout=timeout_ms)
        return {"selector": selector, "found": True, "engine": "playwright"}

    def wait_for_url(self, url: str, timeout_ms: int = 10000) -> dict[str, Any]:
        self._require_page().wait_for_url(url, timeout=timeout_ms)
        return self._page_state(engine="playwright")

    def new_tab(self, url: str = "", wait_seconds: int = 3) -> dict[str, Any]:
        self._ensure_page()
        page = self._context.new_page()
        self._page = page
        if url:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._wait(wait_seconds)
        return self._page_state(engine="playwright")

    def switch_tab(self, tab_index: int) -> dict[str, Any]:
        pages = self._pages()
        if tab_index < 0 or tab_index >= len(pages):
            raise BrowserRuntimeError(f"Tab index out of range: {tab_index}")
        self._page = pages[tab_index]
        self._page.bring_to_front()
        return self._page_state(engine="playwright") | {"tab_index": tab_index}

    def close_tab(self, tab_index: int | None = None) -> dict[str, Any]:
        pages = self._pages()
        index = len(pages) - 1 if tab_index is None else tab_index
        if index < 0 or index >= len(pages):
            raise BrowserRuntimeError(f"Tab index out of range: {index}")
        pages[index].close()
        remaining = self._pages()
        self._page = remaining[-1] if remaining else None
        return {"closed_tab": index, "remaining": len(remaining), "engine": "playwright"}

    def list_tabs(self) -> dict[str, Any]:
        tabs = [
            {"index": index, "url": page.url, "title": self._safe_title(page), "active": page is self._page}
            for index, page in enumerate(self._pages())
        ]
        return {"count": len(tabs), "tabs": tabs, "engine": "playwright"}

    def intercept_network(self, pattern: str, action: str = "log", mock_body: str = "", mock_status: int = 200) -> dict[str, Any]:
        page = self._require_page()
        if pattern in self._route_handlers:
            return {"pattern": pattern, "action": action, "already_active": True, "engine": "playwright"}

        def handler(route: Any, request: Any) -> None:
            matched = pattern in request.url
            if matched:
                self._network_log.append({"url": request.url, "method": request.method, "action": action, "ts": time.time()})
            if not matched or action == "log":
                route.continue_()
            elif action == "block":
                route.abort()
            elif action == "mock":
                route.fulfill(status=mock_status, body=mock_body, content_type="application/json")
            else:
                route.continue_()

        page.route("**/*", handler)
        self._route_handlers[pattern] = handler
        return {"pattern": pattern, "action": action, "active": True, "engine": "playwright"}

    def stop_intercept(self, pattern: str) -> dict[str, Any]:
        page = self._require_page()
        handler = self._route_handlers.pop(pattern, None)
        if handler:
            page.unroute("**/*", handler)
        return {"pattern": pattern, "stopped": bool(handler), "engine": "playwright"}

    def get_network_log(self, limit: int = 20) -> dict[str, Any]:
        return {"count": len(self._network_log), "events": self._network_log[-max(1, int(limit or 20)) :]}

    def get_all_links(self) -> dict[str, Any]:
        page = self._require_page()
        links = page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href]')).slice(0, 200).map((a) => ({
                text: (a.innerText || a.textContent || '').trim().slice(0, 160),
                href: a.href,
                selector: a.id ? `#${CSS.escape(a.id)}` : ''
            }))"""
        )
        return {"url": page.url, "link_count": len(links), "links": links, "engine": "playwright"}

    def get_page_info(self) -> dict[str, Any]:
        return self.page_snapshot(selector="body", limit=30)

    def debug_feedback(self, limit: int = 20) -> dict[str, Any]:
        return {
            "status": self.status(),
            "history": self._history[-max(1, int(limit or 20)) :],
            "network": self._network_log[-max(1, int(limit or 20)) :],
        }

    def status(self) -> dict[str, Any]:
        return {
            "playwright_available": HAS_PLAYWRIGHT,
            "automation_ready": self._page is not None and not self._page.is_closed(),
            "tabs": len(self._pages()) if self._context else 0,
            "active_url": self._page.url if self._page else "",
            "engine": "playwright" if self._page else "idle",
        }

    def close(self) -> dict[str, Any]:
        closed = {"page": False, "context": False, "browser": False, "playwright": False}
        for attr, key in (("_context", "context"), ("_browser", "browser"), ("_playwright", "playwright")):
            obj = getattr(self, attr, None)
            if obj is None:
                continue
            try:
                if key == "playwright":
                    obj.stop()
                else:
                    obj.close()
                closed[key] = True
            except Exception as exc:
                logger.debug("Browser runtime close ignored for %s: %s", key, exc)
            setattr(self, attr, None)
        self._page = None
        self._route_handlers.clear()
        return {"closed": closed, "engine": "playwright"}

    def _ensure_page(self, visible: bool = False, new_session: bool = False) -> Any:
        if not HAS_PLAYWRIGHT or sync_playwright is None:
            raise BrowserRuntimeError("Playwright is not installed; only system-browser fallback is available.")
        if new_session:
            self.close()
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        if self._browser is None:
            self._browser = self._playwright.chromium.launch(headless=not visible)
        if self._context is None:
            self._context = self._browser.new_context(viewport={"width": 1365, "height": 900})
        if self._page is None or self._page.is_closed():
            self._page = self._context.new_page()
        return self._page

    def _require_page(self) -> Any:
        try:
            return self._ensure_page()
        except Exception as exc:
            raise BrowserRuntimeError(f"No active browser page is available: {exc}") from exc

    def _pages(self) -> list[Any]:
        if self._context is None:
            return []
        return [page for page in self._context.pages if not page.is_closed()]

    def _page_state(self, engine: str) -> dict[str, Any]:
        page = self._require_page()
        return {"url": page.url, "title": self._safe_title(page), "engine": engine, "automation_ready": True}

    @staticmethod
    def _safe_title(page: Any) -> str:
        try:
            return page.title()
        except Exception:
            return ""

    @staticmethod
    def _wait(wait_seconds: int) -> None:
        if wait_seconds > 0:
            time.sleep(min(wait_seconds, 10))

    @staticmethod
    def _compact_text(text: str, limit: int = 4000) -> str:
        return re.sub(r"\s+", " ", text or "").strip()[:limit]

    @staticmethod
    def _resolve_screenshot_path(screenshot_path: str = "") -> Path:
        if screenshot_path:
            target = Path(screenshot_path).expanduser().resolve()
        else:
            target = (Path.cwd() / "browser_snapshots" / f"snapshot_{int(time.time())}.png").resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _http_inspect(self, url: str) -> dict[str, Any]:
        request = Request(url, headers={"User-Agent": "ANA-MAX-OS20.1/1.0"})
        with urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
            charset = response.headers.get_content_charset() or "utf-8"
        html_text = raw.decode(charset, errors="replace")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
        title = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else ""
        body_text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", html_text, flags=re.I)
        body_text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", body_text, flags=re.I)
        body_text = html.unescape(re.sub(r"<[^>]+>", " ", body_text))
        links = self._extract_links(html_text, url)
        return {
            "url": url,
            "title": title,
            "text_preview": self._compact_text(body_text),
            "text_length": len(body_text),
            "links": links[:100],
            "link_count": len(links),
            "dom_refs": [],
            "dom_ref_count": 0,
            "engine": "http",
            "automation_ready": False,
        }

    @staticmethod
    def _extract_links(html_text: str, base_url: str) -> list[dict[str, str]]:
        links: list[dict[str, str]] = []
        pattern = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
        for match in pattern.finditer(html_text):
            href = urljoin(base_url, html.unescape(match.group(1).strip()))
            text = html.unescape(re.sub(r"<[^>]+>", " ", match.group(2)))
            links.append({"href": href, "text": re.sub(r"\s+", " ", text).strip()[:160]})
        return links

    def _record(self, action: str, data: dict[str, Any]) -> None:
        self._history.append({"ts": time.time(), "action": action, "data": self._safe_json(data)})
        self._history = self._history[-100:]

    @staticmethod
    def _safe_json(data: dict[str, Any]) -> dict[str, Any]:
        try:
            return json.loads(json.dumps(data, default=str))
        except Exception:
            return {"unserializable": True}


_DOM_REFS_SCRIPT = r"""
(limit) => {
  function cssPath(el) {
    if (!el || !el.tagName) return "";
    if (el.id) return "#" + CSS.escape(el.id);
    const parts = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
      let part = current.tagName.toLowerCase();
      if (current.classList && current.classList.length) {
        part += "." + Array.from(current.classList).slice(0, 2).map((c) => CSS.escape(c)).join(".");
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter((child) => child.tagName === current.tagName);
        if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(current) + 1})`;
      }
      parts.unshift(part);
      current = parent;
    }
    return parts.join(" > ");
  }
  function labelOf(el) {
    const aria = el.getAttribute("aria-label") || el.getAttribute("title") || el.getAttribute("alt") || "";
    const text = (el.innerText || el.textContent || el.value || "").replace(/\s+/g, " ").trim();
    return (aria || text || el.getAttribute("placeholder") || "").slice(0, 180);
  }
  const selector = [
    "a[href]", "button", "input", "select", "textarea", "summary",
    "[role]", "[onclick]", "[tabindex]", "[aria-label]", "[contenteditable='true']"
  ].join(",");
  return Array.from(document.querySelectorAll(selector))
    .filter((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
    })
    .slice(0, limit)
    .map((el, index) => {
      const rect = el.getBoundingClientRect();
      return {
        ref: `b${index}`,
        tag: el.tagName.toLowerCase(),
        role: el.getAttribute("role") || "",
        name: labelOf(el),
        selector: cssPath(el),
        href: el.href || "",
        type: el.getAttribute("type") || "",
        disabled: Boolean(el.disabled || el.getAttribute("aria-disabled") === "true"),
        checked: Boolean(el.checked || el.getAttribute("aria-checked") === "true"),
        rect: {x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height)}
      };
    });
}
"""
