"""
Persistent browser automation runtime for ANA Engineer.
Suporta: JS eval, tabs multiple, network intercept, scroll, hover,
         screenshot cu base64, drag-drop, upload, select, analiza vizuala.
"""

from __future__ import annotations

import base64
import time
import uuid
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Route
    HAS_PLAYWRIGHT = True
except ImportError:
    sync_playwright = None
    PlaywrightTimeoutError = RuntimeError
    Route = None
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)


class BrowserRuntimeError(RuntimeError):
    """Raised when a browser automation session cannot continue."""


@dataclass
class BrowserSessionState:
    session_id: str
    started_at: float
    visible: bool
    current_url: str = ""
    title: str = ""
    last_selector: str = ""
    last_screenshot: str = ""
    console_errors: List[Dict[str, Any]] = field(default_factory=list)
    network_failures: List[Dict[str, Any]] = field(default_factory=list)
    active_tab_index: int = 0
    tab_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BrowserAutomationRuntime:
    """Manage a persistent Playwright browser page for Engineer actions."""

    def __init__(self) -> None:
        self._playwright_cm = None
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._browser_executable: Optional[str] = None
        self.state: Optional[BrowserSessionState] = None
        self._console_errors: List[Dict[str, Any]] = []
        self._network_failures: List[Dict[str, Any]] = []
        self._network_log: List[Dict[str, Any]] = []
        self._pages: List[Any] = []           # lista de tab-uri
        self._intercepted_routes: Dict[str, str] = {}  # pattern -> action

    def open(self, url: str, visible: bool = True, new_session: bool = False,
             wait_seconds: int = 2) -> Dict[str, Any]:
        if new_session or self.page is None:
            self._start_session(visible=visible)
        elif self.state:
            self.state.visible = visible

        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if wait_seconds > 0:
            self.page.wait_for_timeout(wait_seconds * 1000)
        return self._capture_state(url=url)

    def navigate(self, url: str, wait_seconds: int = 2) -> Dict[str, Any]:
        self._require_page()
        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if wait_seconds > 0:
            self.page.wait_for_timeout(wait_seconds * 1000)
        return self._capture_state(url=url)

    def click(self, selector: str, wait_seconds: int = 1) -> Dict[str, Any]:
        page = self._require_page()
        page.locator(selector).first.click(timeout=10000)
        if wait_seconds > 0:
            page.wait_for_timeout(wait_seconds * 1000)
        return self._capture_state(selector=selector)

    def type(self, selector: str, text: str, clear: bool = True, wait_seconds: int = 1) -> Dict[str, Any]:
        page = self._require_page()
        locator = page.locator(selector).first
        if clear:
            locator.fill("")
        locator.type(text, delay=20)
        if wait_seconds > 0:
            page.wait_for_timeout(wait_seconds * 1000)
        return self._capture_state(selector=selector)

    def press(self, selector: str, key: str, wait_seconds: int = 1) -> Dict[str, Any]:
        page = self._require_page()
        page.locator(selector).first.press(key)
        if wait_seconds > 0:
            page.wait_for_timeout(wait_seconds * 1000)
        return self._capture_state(selector=selector)

    def read(self, selector: str = "body", limit_chars: int = 3000) -> Dict[str, Any]:
        page = self._require_page()
        text = page.locator(selector).first.inner_text(timeout=5000)
        state = self._capture_state(selector=selector)
        state["text"] = text[:limit_chars]
        return state

    def inspect(
        self,
        url: str = "",
        selector: str = "body",
        wait_seconds: int = 2,
        screenshot_path: str = "",
        limit_chars: int = 3000,
    ) -> Dict[str, Any]:
        """
        Inspecteaza pagina curenta sau deschide/navigheaza la un URL si returneaza
        un snapshot util pentru debugging de tip "F12".
        """
        if self.page is None:
            if not url:
                raise BrowserRuntimeError("Nu exista o sesiune browser activa si nici URL pentru inspectie.")
            self.open(url, visible=False, new_session=True, wait_seconds=wait_seconds)
        elif url and self.page.url != url:
            self.navigate(url, wait_seconds=wait_seconds)

        page = self._require_page()
        target = self._resolve_screenshot_path(screenshot_path)
        page.screenshot(path=str(target), full_page=True)

        try:
            text = page.locator(selector).first.inner_text(timeout=5000)
        except Exception:
            text = ""

        try:
            outer_html = page.eval_on_selector(selector, "el => el.outerHTML")
        except Exception:
            outer_html = ""

        state = self._capture_state(url=url or page.url, selector=selector, screenshot_path=str(target))
        state["text_preview"] = text[:limit_chars]
        state["html_preview"] = outer_html[:limit_chars]
        state["screenshot_path"] = str(target)
        state["engine"] = "playwright_runtime"
        state["automation_ready"] = True
        state["page_info"] = self.get_page_info().get("page_info", {})
        state["debug_feedback"] = {
            "console_errors": self._console_errors[-20:],
            "network_failures": self._network_failures[-20:],
            "console_error_count": len(self._console_errors),
            "network_failure_count": len(self._network_failures),
        }
        return state

    # ------------------------------------------------------------------ #
    #  JS EVAL / DEVTOOLS                                                  #
    # ------------------------------------------------------------------ #

    def evaluate(self, script: str) -> Dict[str, Any]:
        """Executa JavaScript direct in pagina (DevTools mode)."""
        page = self._require_page()
        try:
            result = page.evaluate(script)
            state = self._capture_state()
            state["js_result"] = result
            return state
        except Exception as exc:
            state = self._capture_state()
            state["js_error"] = str(exc)
            return state

    def evaluate_on_selector(self, selector: str, script: str) -> Dict[str, Any]:
        """Executa JS pe un element specific: (el) => el.value"""
        page = self._require_page()
        try:
            result = page.eval_on_selector(selector, script)
            state = self._capture_state(selector=selector)
            state["js_result"] = result
            return state
        except Exception as exc:
            state = self._capture_state()
            state["js_error"] = str(exc)
            return state

    # ------------------------------------------------------------------ #
    #  SCROLL, HOVER, DRAG, SELECT, UPLOAD                                 #
    # ------------------------------------------------------------------ #

    def scroll(self, selector: str = "body", direction: str = "down",
               amount: int = 500) -> Dict[str, Any]:
        """Scroll in pagina sau intr-un element."""
        page = self._require_page()
        if selector == "body":
            if direction == "down":
                page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "top":
                page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        else:
            page.locator(selector).first.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        return self._capture_state(selector=selector)

    def hover(self, selector: str) -> Dict[str, Any]:
        """Hover (mouse over) pe un element."""
        page = self._require_page()
        page.locator(selector).first.hover()
        page.wait_for_timeout(300)
        return self._capture_state(selector=selector)

    def select_option(self, selector: str, value: str) -> Dict[str, Any]:
        """Selecteaza o optiune dintr-un <select>."""
        page = self._require_page()
        page.locator(selector).first.select_option(value)
        page.wait_for_timeout(300)
        return self._capture_state(selector=selector)

    def upload_file(self, selector: str, file_path: str) -> Dict[str, Any]:
        """Upload fisier intr-un <input type=file>."""
        page = self._require_page()
        page.locator(selector).first.set_input_files(file_path)
        page.wait_for_timeout(500)
        return self._capture_state(selector=selector)

    def get_attribute(self, selector: str, attribute: str) -> Dict[str, Any]:
        """Citeste un atribut HTML de pe un element."""
        page = self._require_page()
        value = page.locator(selector).first.get_attribute(attribute)
        state = self._capture_state(selector=selector)
        state["attribute"] = attribute
        state["value"] = value
        return state

    def wait_for_selector(self, selector: str, timeout_ms: int = 10000) -> Dict[str, Any]:
        """Asteapta pana apare un selector in DOM."""
        page = self._require_page()
        page.wait_for_selector(selector, timeout=timeout_ms)
        return self._capture_state(selector=selector)

    def wait_for_url(self, url_pattern: str, timeout_ms: int = 15000) -> Dict[str, Any]:
        """Asteapta pana URL-ul curent contine un pattern."""
        page = self._require_page()
        page.wait_for_url(f"**{url_pattern}**", timeout=timeout_ms)
        return self._capture_state()

    # ------------------------------------------------------------------ #
    #  TABS MULTIPLE                                                       #
    # ------------------------------------------------------------------ #

    def new_tab(self, url: str = "", wait_seconds: int = 2) -> Dict[str, Any]:
        """Deschide un tab nou si comuta la el."""
        if self.context is None:
            raise BrowserRuntimeError("Nu exista o sesiune activa. Ruleaza mai intai operation=open.")
        new_page = self.context.new_page()
        self._attach_debug_listeners(new_page)
        self._pages.append(new_page)
        self.page = new_page
        if self.state:
            self.state.tab_count = len(self._pages)
            self.state.active_tab_index = len(self._pages) - 1
        if url:
            normalized = url if url.startswith("http") else f"https://{url}"
            new_page.goto(normalized, wait_until="domcontentloaded", timeout=30000)
            if wait_seconds > 0:
                new_page.wait_for_timeout(wait_seconds * 1000)
        state = self._capture_state(url=url)
        state["new_tab_index"] = len(self._pages) - 1
        return state

    def switch_tab(self, index: int) -> Dict[str, Any]:
        """Comuta la un alt tab dupa index (0-based)."""
        if not self._pages:
            raise BrowserRuntimeError("Nu exista tab-uri deschise.")
        if index < 0 or index >= len(self._pages):
            raise BrowserRuntimeError(f"Index tab invalid: {index}. Disponibile: 0-{len(self._pages)-1}")
        self.page = self._pages[index]
        if self.state:
            self.state.active_tab_index = index
        return self._capture_state()

    def close_tab(self, index: Optional[int] = None) -> Dict[str, Any]:
        """Inchide tab-ul curent sau cel cu index specificat."""
        if not self._pages:
            raise BrowserRuntimeError("Nu exista tab-uri de inchis.")
        idx = index if index is not None else (self.state.active_tab_index if self.state else 0)
        if idx < 0 or idx >= len(self._pages):
            idx = len(self._pages) - 1
        page_to_close = self._pages.pop(idx)
        try:
            page_to_close.close()
        except Exception:
            pass
        # comuta la ultimul tab ramas
        if self._pages:
            self.page = self._pages[-1]
            if self.state:
                self.state.active_tab_index = len(self._pages) - 1
                self.state.tab_count = len(self._pages)
        else:
            self.page = None
        state = self._capture_state() if self.page else {"closed_tab": idx, "tabs_remaining": 0}
        state["closed_tab"] = idx
        state["tabs_remaining"] = len(self._pages)
        return state

    def list_tabs(self) -> Dict[str, Any]:
        """Listeaza toate tab-urile deschise."""
        tabs = []
        for i, p in enumerate(self._pages):
            try:
                tabs.append({"index": i, "url": p.url, "title": p.title()})
            except Exception:
                tabs.append({"index": i, "url": "unknown", "title": "unknown"})
        return {
            "tabs": tabs,
            "active_tab": self.state.active_tab_index if self.state else 0,
            "count": len(tabs),
        }

    # ------------------------------------------------------------------ #
    #  NETWORK INTERCEPT                                                   #
    # ------------------------------------------------------------------ #

    def intercept_network(self, pattern: str, action: str = "log",
                          mock_body: str = "", mock_status: int = 200) -> Dict[str, Any]:
        """
        Intercepteaza request-uri care se potrivesc cu pattern-ul.
        action: 'log' | 'block' | 'mock'
        """
        page = self._require_page()
        self._intercepted_routes[pattern] = action

        def handler(route: Any) -> None:
            request = route.request
            entry = {
                "url": request.url,
                "method": request.method,
                "action": action,
                "timestamp": time.time(),
            }
            self._network_log.append(entry)
            logger.debug("Intercepted request: %s %s -> %s", request.method, request.url, action)

            if action == "block":
                route.abort()
            elif action == "mock":
                route.fulfill(
                    status=mock_status,
                    content_type="application/json",
                    body=mock_body or '{"mocked": true}',
                )
            else:
                route.continue_()

        page.route(f"**{pattern}**", handler)
        return {
            "intercepting": True,
            "pattern": pattern,
            "action": action,
            "message": f"Network intercept activ pentru: {pattern}",
        }

    def stop_intercept(self, pattern: str) -> Dict[str, Any]:
        """Opreste interceptarea pentru un pattern."""
        page = self._require_page()
        try:
            page.unroute(f"**{pattern}**")
            self._intercepted_routes.pop(pattern, None)
        except Exception as exc:
            return {"error": str(exc)}
        return {"stopped": True, "pattern": pattern}

    def get_network_log(self, limit: int = 50) -> Dict[str, Any]:
        """Returneaza log-ul de request-uri interceptate."""
        return {
            "log": self._network_log[-limit:],
            "total": len(self._network_log),
            "active_intercepts": list(self._intercepted_routes.keys()),
        }

    # ------------------------------------------------------------------ #
    #  SCREENSHOT CU BASE64 (pentru analiza vizuala AI)                   #
    # ------------------------------------------------------------------ #

    def screenshot_base64(self, selector: str = "") -> Dict[str, Any]:
        """
        Face screenshot si returneaza imaginea ca base64 string.
        Poate fi trimis direct unui model vision AI (Gemini, GPT-4o etc.)
        """
        page = self._require_page()
        if selector:
            try:
                img_bytes = page.locator(selector).first.screenshot()
            except Exception:
                img_bytes = page.screenshot(full_page=False)
        else:
            img_bytes = page.screenshot(full_page=False)

        b64 = base64.b64encode(img_bytes).decode("utf-8")
        state = self._capture_state(selector=selector)
        state["screenshot_base64"] = b64
        state["image_size_kb"] = round(len(img_bytes) / 1024, 1)
        state["ready_for_vision_ai"] = True
        return state

    # ------------------------------------------------------------------ #
    #  GET ALL TEXT / LINKS / FORMS                                        #
    # ------------------------------------------------------------------ #

    def get_all_links(self) -> Dict[str, Any]:
        """Extrage toate link-urile din pagina curenta."""
        page = self._require_page()
        links = page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.innerText.trim().substring(0, 100),
                href: a.href,
                visible: a.offsetParent !== null
            }))
        """)
        state = self._capture_state()
        state["links"] = links
        state["link_count"] = len(links)
        return state

    def get_page_info(self) -> Dict[str, Any]:
        """Info complet despre pagina: titlu, meta, h1-h3, forms, links."""
        page = self._require_page()
        info = page.evaluate("""
            () => ({
                title: document.title,
                url: window.location.href,
                meta_description: (document.querySelector('meta[name=description]') || {}).content || '',
                h1: Array.from(document.querySelectorAll('h1')).map(e => e.innerText.trim()).slice(0, 5),
                h2: Array.from(document.querySelectorAll('h2')).map(e => e.innerText.trim()).slice(0, 10),
                forms: Array.from(document.querySelectorAll('form')).map(f => ({
                    id: f.id,
                    action: f.action,
                    inputs: Array.from(f.querySelectorAll('input,textarea,select')).map(i => ({
                        type: i.type || i.tagName.toLowerCase(),
                        name: i.name,
                        placeholder: i.placeholder || ''
                    }))
                })),
                buttons: Array.from(document.querySelectorAll('button,[role=button]')).map(b => b.innerText.trim()).slice(0, 20),
                link_count: document.querySelectorAll('a[href]').length,
                image_count: document.querySelectorAll('img').length,
            })
        """)
        state = self._capture_state()
        state["page_info"] = info
        return state

    def screenshot(self, screenshot_path: str = "") -> Dict[str, Any]:
        page = self._require_page()
        target = self._resolve_screenshot_path(screenshot_path)
        page.screenshot(path=str(target), full_page=True)
        return self._capture_state(screenshot_path=str(target))

    def debug_feedback(self, limit: int = 20) -> Dict[str, Any]:
        self._require_page()
        state = self._capture_state()
        state["console_errors"] = self._console_errors[-limit:]
        state["network_failures"] = self._network_failures[-limit:]
        state["console_error_count"] = len(self._console_errors)
        state["network_failure_count"] = len(self._network_failures)
        return state

    def close(self) -> Dict[str, Any]:
        state = self.status()
        last_state = state.get("state")
        for obj_name in ("page", "context", "browser"):
            obj = getattr(self, obj_name)
            if obj is not None:
                try:
                    obj.close()
                except Exception:
                    pass
                setattr(self, obj_name, None)

        if self._playwright_cm is not None:
            try:
                self._playwright_cm.__exit__(None, None, None)
            except Exception:
                pass

        self._playwright_cm = None
        self._playwright = None
        self.state = None
        self._pages = []
        self._intercepted_routes = {}
        self._console_errors = []
        self._network_failures = []
        self._network_log = []
        self._browser_executable = None
        state["browser_executable"] = None
        state["session_active"] = False
        state["state"] = last_state
        state["closed"] = True
        return state

    def status(self) -> Dict[str, Any]:
        return {
            "playwright_available": HAS_PLAYWRIGHT,
            "session_active": self.page is not None and self.state is not None,
            "browser_executable": self._browser_executable,
            "install_hint": self.install_hint(),
            "state": self.state.to_dict() if self.state else None,
            "console_error_count": len(self._console_errors),
            "network_failure_count": len(self._network_failures),
        }

    @staticmethod
    def install_hint() -> str:
        return "Ruleaza: venv\\Scripts\\python.exe -m playwright install chromium"

    def _start_session(self, visible: bool) -> None:
        self._ensure_playwright()
        if self.browser is not None or self.context is not None or self.page is not None:
            self.close()

        self._playwright_cm = sync_playwright()
        self._playwright = self._playwright_cm.__enter__()
        try:
            self.browser = self._launch_browser(headless=not visible)
        except Exception as exc:
            self._reset_runtime()
            raise BrowserRuntimeError(
                f"Browser runtime indisponibil: {exc}. {self.install_hint()}"
            ) from exc

        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self._pages = [self.page]
        self._console_errors = []
        self._network_failures = []
        self._network_log = []
        self._intercepted_routes = {}
        self._attach_debug_listeners(self.page)
        self.state = BrowserSessionState(
            session_id=f"browser_{uuid.uuid4().hex[:8]}",
            started_at=time.time(),
            visible=visible,
            tab_count=1,
            active_tab_index=0,
        )
        logger.info("Browser session started: %s", self.state.session_id)

    def _launch_browser(self, headless: bool):
        launch_errors: List[str] = []
        try:
            self._browser_executable = None
            return self._playwright.chromium.launch(headless=headless)
        except Exception as exc:
            launch_errors.append(f"bundled chromium: {exc}")

        for candidate in self._candidate_browser_paths():
            if not candidate.exists():
                continue
            try:
                browser = self._playwright.chromium.launch(
                    executable_path=str(candidate),
                    headless=headless,
                )
                self._browser_executable = str(candidate)
                logger.info("Browser runtime fallback executable: %s", candidate)
                return browser
            except Exception as exc:
                launch_errors.append(f"{candidate.name}: {exc}")

        joined_errors = " | ".join(launch_errors[:4])
        raise BrowserRuntimeError(f"Nu am putut lansa Chromium/Chrome local ({joined_errors})")

    def _capture_state(self, url: Optional[str] = None, selector: str = "",
                       screenshot_path: str = "") -> Dict[str, Any]:
        page = self._require_page()
        if self.state is None:
            raise BrowserRuntimeError("Browser session state is missing")

        self.state.current_url = url or page.url
        self.state.title = page.title()
        if selector:
            self.state.last_selector = selector
        if screenshot_path:
            self.state.last_screenshot = screenshot_path
        self.state.console_errors = self._console_errors[-20:]
        self.state.network_failures = self._network_failures[-20:]

        state = self.state.to_dict()
        state["url"] = page.url
        state["title"] = self.state.title
        state["browser_executable"] = self._browser_executable
        return state

    def _require_page(self):
        if self.page is None or self.state is None:
            raise BrowserRuntimeError("Nu exista o sesiune browser activa. Ruleaza mai intai operation=open.")
        return self.page

    def _attach_debug_listeners(self, page) -> None:
        def on_console(msg) -> None:
            try:
                msg_type = msg.type
                text = msg.text
                if msg_type in {"error", "warning", "assert"}:
                    self._console_errors.append(
                        {
                            "type": msg_type,
                            "text": text[:1000],
                            "location": getattr(msg, "location", None),
                            "timestamp": time.time(),
                        }
                    )
            except Exception:
                logger.debug("Failed to capture browser console message", exc_info=True)

        def on_request_failed(request) -> None:
            try:
                failure = request.failure
                self._network_failures.append(
                    {
                        "url": request.url,
                        "method": request.method,
                        "resource_type": request.resource_type,
                        "error_text": (failure or {}).get("errorText", ""),
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                logger.debug("Failed to capture browser network failure", exc_info=True)

        page.on("console", on_console)
        page.on("requestfailed", on_request_failed)

    def _ensure_playwright(self) -> None:
        if not HAS_PLAYWRIGHT:
            raise BrowserRuntimeError(
                f"Playwright nu este instalat. {self.install_hint()}"
            )

    def _reset_runtime(self) -> None:
        self.browser = None
        self.context = None
        self.page = None
        self.state = None
        self._console_errors = []
        self._network_failures = []
        self._network_log = []
        self._pages = []
        self._intercepted_routes = {}
        self._browser_executable = None
        if self._playwright_cm is not None:
            try:
                self._playwright_cm.__exit__(None, None, None)
            except Exception:
                pass
        self._playwright_cm = None
        self._playwright = None

    @staticmethod
    def _resolve_screenshot_path(screenshot_path: str) -> Path:
        if screenshot_path:
            target = Path(screenshot_path).resolve()
        else:
            target = (Path.cwd() / "browser_snapshots" / f"snapshot_{int(time.time())}.png").resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _candidate_browser_paths() -> List[Path]:
        # Chrome is the most reliable target for ANA's browser workflows on
        # Windows because it exposes predictable process and automation behavior.
        return [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]


_RUNTIME: Optional[BrowserAutomationRuntime] = None


def get_browser_runtime() -> BrowserAutomationRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = BrowserAutomationRuntime()
    return _RUNTIME
