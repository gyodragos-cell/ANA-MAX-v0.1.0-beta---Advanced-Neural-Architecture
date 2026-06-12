"""
Visible browser launch and lightweight inspection helpers.
"""

from __future__ import annotations

import re
import time
import logging
import webbrowser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname
import warnings

import urllib3

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus
from core.browser_runtime import BrowserRuntimeError, get_browser_runtime

logger = logging.getLogger(__name__)


class BrowserControlTool(Tool):
    """Open the local browser or inspect a page with a lightweight snapshot."""

    @property
    def run_in_worker_thread(self) -> bool:
        # Playwright sync objects are thread-affine; keep persistent sessions on
        # the registry caller thread so follow-up browser operations can reuse
        # the same page without greenlet/thread errors.
        return False

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="browser_control",
            description="Deschide browserul local sau inspecteaza o pagina web cu screenshot si extras text.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Actiunea dorita",
                    type="string",
                    required=True,
                    choices=[
                    "open", "inspect", "navigate", "click", "type", "press", "read",
                    "screenshot", "screenshot_base64", "debug_feedback", "close", "status",
                    "evaluate", "evaluate_on_selector",
                    "scroll", "hover", "select_option", "upload_file",
                    "get_attribute", "wait_for_selector", "wait_for_url",
                    "new_tab", "switch_tab", "close_tab", "list_tabs",
                    "intercept_network", "stop_intercept", "get_network_log",
                    "get_all_links", "get_page_info", "dom_refs", "page_snapshot",
                ],
                ),
                ToolParameter(
                    name="url",
                    description="URL-ul tinta",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="selector",
                    description="Selector CSS pentru click/type/read",
                    type="string",
                    required=False,
                    default="body",
                ),
                ToolParameter(
                    name="text",
                    description="Textul de tastat in elementul selectat",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="key",
                    description="Tasta pentru operatia press",
                    type="string",
                    required=False,
                    default="Enter",
                ),
                ToolParameter(
                    name="wait_seconds",
                    description="Timp de asteptare pentru incarcare",
                    type="integer",
                    required=False,
                    default=3,
                ),
                ToolParameter(
                    name="screenshot_path",
                    description="Calea screenshot-ului pentru inspect",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="visible",
                    description="Deschide browserul vizibil pentru operation=open",
                    type="boolean",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="new_session",
                    description="Forteaza o sesiune browser noua",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="limit",
                    description="Numar maxim de evenimente debug returnate",
                    type="integer",
                    required=False,
                    default=20,
                ),
                ToolParameter(
                    name="script",
                    description="Cod JavaScript de executat in pagina",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="direction",
                    description="Directia scroll: up | down | top | bottom",
                    type="string",
                    required=False,
                    default="down",
                ),
                ToolParameter(
                    name="amount",
                    description="Numarul de pixeli pentru scroll",
                    type="integer",
                    required=False,
                    default=500,
                ),
                ToolParameter(
                    name="attribute",
                    description="Atribut HTML de citit (ex: href, value, class)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="tab_index",
                    description="Index tab (0-based) pentru switch_tab / close_tab",
                    type="integer",
                    required=False,
                    default=0,
                ),
                ToolParameter(
                    name="pattern",
                    description="Pattern URL pentru intercept_network (ex: /api/, .jpg)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="action",
                    description="Actiune intercept: log | block | mock",
                    type="string",
                    required=False,
                    default="log",
                ),
                ToolParameter(
                    name="mock_body",
                    description="Body JSON pentru raspuns mock",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="mock_status",
                    description="HTTP status code pentru mock (default 200)",
                    type="integer",
                    required=False,
                    default=200,
                ),
                ToolParameter(
                    name="timeout_ms",
                    description="Timeout in ms pentru wait_for_selector / wait_for_url",
                    type="integer",
                    required=False,
                    default=10000,
                ),
                ToolParameter(
                    name="file_path",
                    description="Calea fisierului pentru upload",
                    type="string",
                    required=False,
                    default="",
                ),
            ],
            category="browser",
            requires_confirmation=False,
        )

    def execute(self, operation: str, url: str = "", **kwargs) -> ToolResult:
        wait_seconds = int(kwargs.get("wait_seconds", 3) or 3)
        screenshot_path = kwargs.get("screenshot_path", "")
        selector = kwargs.get("selector", "body") or "body"
        text = kwargs.get("text", "")
        key = kwargs.get("key", "Enter")
        visible = self._to_bool(kwargs.get("visible", True))
        new_session = self._to_bool(kwargs.get("new_session", False))
        limit = int(kwargs.get("limit", 20) or 20)
        script = kwargs.get("script", "")
        direction = kwargs.get("direction", "down")
        amount = int(kwargs.get("amount", 500) or 500)
        attribute = kwargs.get("attribute", "")
        tab_index = int(kwargs.get("tab_index", 0) or 0)
        pattern = kwargs.get("pattern", "")
        action = kwargs.get("action", "log")
        mock_body = kwargs.get("mock_body", "")
        mock_status = int(kwargs.get("mock_status", 200) or 200)
        timeout_ms = int(kwargs.get("timeout_ms", 10000) or 10000)
        file_path = kwargs.get("file_path", "")

        try:
            runtime = get_browser_runtime()

            if operation == "open":
                normalized_url = self._normalize_url(url)
                if not normalized_url:
                    return ToolResult(status=ToolStatus.ERROR, error=f"URL invalid: {url}")
                data = runtime.open(normalized_url, visible=visible, new_session=new_session, wait_seconds=wait_seconds)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Browser deschis la {normalized_url}")

            if operation == "navigate":
                normalized_url = self._normalize_url(url)
                if not normalized_url:
                    return ToolResult(status=ToolStatus.ERROR, error=f"URL invalid: {url}")
                data = runtime.navigate(normalized_url, wait_seconds=wait_seconds)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Browser navigat la {normalized_url}")

            if operation == "click":
                data = runtime.click(selector, wait_seconds=wait_seconds)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Click executat pe {selector}")

            if operation == "type":
                data = runtime.type(selector, text=text, wait_seconds=wait_seconds)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Text introdus in {selector}")

            if operation == "press":
                data = runtime.press(selector, key=key, wait_seconds=wait_seconds)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Tasta {key} trimisa catre {selector}")

            if operation == "read":
                data = runtime.read(selector=selector)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Continut extras din {selector}")

            if operation == "screenshot":
                data = runtime.screenshot(screenshot_path=screenshot_path)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Screenshot browser salvat")

            if operation == "screenshot_base64":
                data = runtime.screenshot_base64(selector=selector if selector != "body" else "")
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Screenshot base64 gata pentru AI vision")

            if operation == "debug_feedback":
                data = runtime.debug_feedback(limit=limit)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Feedback debug browser disponibil")

            if operation == "close":
                data = runtime.close()
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Sesiunea browser a fost inchisa")

            if operation == "status":
                return ToolResult(status=ToolStatus.SUCCESS, data=runtime.status(), message="Status browser")

            # -- JS EVAL ------------------------------------------------
            if operation == "evaluate":
                if not script:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'script' este necesar")
                data = runtime.evaluate(script)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="JavaScript executat in pagina")

            if operation == "evaluate_on_selector":
                if not script:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'script' este necesar")
                data = runtime.evaluate_on_selector(selector, script)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"JavaScript executat pe {selector}")

            # -- SCROLL / HOVER / INTERACT ------------------------------
            if operation == "scroll":
                data = runtime.scroll(selector=selector, direction=direction, amount=amount)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Scroll {direction} {amount}px")

            if operation == "hover":
                data = runtime.hover(selector)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Hover pe {selector}")

            if operation == "select_option":
                data = runtime.select_option(selector, value=text)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Optiune selectata in {selector}")

            if operation == "upload_file":
                if not file_path:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'file_path' este necesar")
                data = runtime.upload_file(selector, file_path)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Fisier uploadat in {selector}")

            if operation == "get_attribute":
                if not attribute:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'attribute' este necesar")
                data = runtime.get_attribute(selector, attribute)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Atribut '{attribute}' citit din {selector}")

            if operation == "wait_for_selector":
                data = runtime.wait_for_selector(selector, timeout_ms=timeout_ms)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Selector '{selector}' aparut in DOM")

            if operation == "wait_for_url":
                data = runtime.wait_for_url(url, timeout_ms=timeout_ms)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"URL ajuns la pattern: {url}")

            # -- TABS ---------------------------------------------------
            if operation == "new_tab":
                data = runtime.new_tab(url=url, wait_seconds=wait_seconds)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Tab nou deschis{' la ' + url if url else ''}")

            if operation == "switch_tab":
                data = runtime.switch_tab(tab_index)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Comutat la tab {tab_index}")

            if operation == "close_tab":
                data = runtime.close_tab(tab_index if tab_index else None)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Tab inchis")

            if operation == "list_tabs":
                data = runtime.list_tabs()
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Tab-uri deschise: {data['count']}")

            # -- NETWORK INTERCEPT --------------------------------------
            if operation == "intercept_network":
                if not pattern:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'pattern' este necesar")
                data = runtime.intercept_network(pattern=pattern, action=action,
                                                  mock_body=mock_body, mock_status=mock_status)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Network intercept activ: {pattern}")

            if operation == "stop_intercept":
                if not pattern:
                    return ToolResult(status=ToolStatus.ERROR, error="Parametrul 'pattern' este necesar")
                data = runtime.stop_intercept(pattern)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Intercept oprit: {pattern}")

            if operation == "get_network_log":
                data = runtime.get_network_log(limit=limit)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Network log returnat")

            # -- PAGE INFO ----------------------------------------------
            if operation == "get_all_links":
                data = runtime.get_all_links()
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"Extrase {data.get('link_count', 0)} link-uri")

            if operation == "get_page_info":
                data = runtime.get_page_info()
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Info pagina extras")

            if operation == "dom_refs":
                data = runtime.dom_refs(limit=limit)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message=f"DOM refs extrase: {data.get('count', 0)}")

            if operation == "page_snapshot":
                data = runtime.page_snapshot(selector=selector, limit=limit)
                return ToolResult(status=ToolStatus.SUCCESS, data=data, message="Snapshot pagina extras")

            if operation == "inspect":
                normalized_url = self._normalize_url(url) if url else ""
                if url and not normalized_url:
                    return ToolResult(status=ToolStatus.ERROR, error=f"URL invalid: {url}")
                data = runtime.inspect(
                    url=normalized_url,
                    selector=selector,
                    wait_seconds=wait_seconds,
                    screenshot_path=screenshot_path,
                )
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data=data,
                    message=f"Pagina a fost inspectata: {normalized_url or data.get('url', '')}",
                )

        except BrowserRuntimeError as exc:
            if operation == "open":
                normalized_url = self._normalize_url(url)
                opened = bool(normalized_url) and webbrowser.open(normalized_url)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "url": normalized_url,
                        "opened": bool(opened),
                        "fallback": "system_browser",
                        "automation_ready": False,
                    },
                    message=f"Browser deschis la {normalized_url}, dar sesiunea Playwright nu este pregatita inca.",
                )
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=f"Browser control failed: {exc}")

        return ToolResult(status=ToolStatus.ERROR, error=f"Operatie browser necunoscuta: {operation}")

    def _inspect(self, url: str, wait_seconds: int = 3, screenshot_path: str = "") -> ToolResult:
        if HAS_PLAYWRIGHT:
            try:
                return self._inspect_with_playwright(url, wait_seconds=wait_seconds, screenshot_path=screenshot_path)
            except Exception as exc:
                logger.warning("Playwright inspect failed for %s: %s", url, exc)

        if HAS_REQUESTS:
            return self._inspect_with_requests(url)

        return ToolResult(
            status=ToolStatus.ERROR,
            error="Inspectia browser necesita Playwright sau requests instalat.",
        )

    def _inspect_with_playwright(self, url: str, wait_seconds: int = 3, screenshot_path: str = "") -> ToolResult:
        screenshot_file = self._resolve_screenshot_path(screenshot_path)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if wait_seconds > 0:
                page.wait_for_timeout(wait_seconds * 1000)
            title = page.title()
            body_text = page.locator("body").inner_text(timeout=5000)
            page.screenshot(path=str(screenshot_file), full_page=True)
            browser.close()

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "url": url,
                "title": title,
                "text_preview": body_text[:1200],
                "screenshot_path": str(screenshot_file),
                "engine": "playwright",
            },
            message=f"Pagina a fost inspectata: {url}",
        )

    def _inspect_with_requests(self, url: str) -> ToolResult:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
        except requests.exceptions.SSLError:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                response = requests.get(url, timeout=20, verify=False)
                response.raise_for_status()
        html = response.text
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "url": url,
                "title": title,
                "text_preview": text[:1200],
                "engine": "requests",
            },
            message=f"Pagina a fost inspectata: {url}",
        )

    @staticmethod
    def _normalize_url(url: str) -> str:
        candidate = (url or "").strip()
        if not candidate:
            return ""
        if candidate == "about:blank":
            return candidate
        if candidate.lower().startswith("www."):
            candidate = f"https://{candidate}"
        parsed = urlparse(candidate)
        if parsed.scheme.lower() == "file":
            if parsed.netloc and parsed.netloc.lower() != "localhost":
                return ""
            try:
                target = Path(url2pathname(parsed.path)).resolve()
                workspace = Path(__file__).resolve().parents[2]
                if target != workspace and workspace not in target.parents:
                    return ""
                return target.as_uri()
            except Exception:
                return ""
        if not (parsed.scheme and parsed.netloc):
            return ""
        return candidate

    @staticmethod
    def _to_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "no", ""}
        return bool(value)

    @staticmethod
    def _resolve_screenshot_path(screenshot_path: str) -> Path:
        if screenshot_path:
            target = Path(screenshot_path).resolve()
        else:
            target = (Path.cwd() / "browser_snapshots" / f"snapshot_{int(time.time())}.png").resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
