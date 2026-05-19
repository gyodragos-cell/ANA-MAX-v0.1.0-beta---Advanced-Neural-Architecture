"""
Web Scraper Tool - Advanced Web Fetching & Parsing
Author: ANA_MAX
Date: 2026-05-12
Category: web

Functions:
- fetch_url: Get HTML content from URL
- parse_html: Parse HTML with BeautifulSoup
- extract_links: Extract all links from page
- extract_text: Extract plain text
- extract_images: Extract image URLs
- scrape_multiple: Scrape multiple URLs
- download_file: Download file from URL

Requires: requests, beautifulsoup4 (optional)
"""

from __future__ import annotations

import re
import os
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
from pathlib import Path

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class WebScraperTool(Tool):
    """Tool pentru web scraping si fetch content."""

    def __init__(self) -> None:
        self._requests_available = self._check_library("requests")
        self._bs4_available = self._check_library("bs4")

    def _check_library(self, name: str) -> bool:
        """Verifica daca o librarie e disponibila."""
        try:
            __import__(name)
            return True
        except ImportError:
            return False

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_scraper",
            description="Web scraping: fetch URL, parse HTML, extrage linkuri/text/imagini, download fisiere.",
            parameters=[
                ToolParameter(
                    name="operation",
                    description="Operatia de executat",
                    type="string",
                    required=True,
                    choices=[
                        "fetch", "parse", "extract_links", "extract_text",
                        "extract_images", "scrape_multiple", "download",
                        "extract_metadata", "extract_forms"
                    ],
                ),
                ToolParameter(
                    name="url",
                    description="URL pentru fetch/scrape",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="html",
                    description="HTML content (pentru parse)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="selector",
                    description="CSS selector pentru extragere",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="urls",
                    description="Lista URL-uri JSON (pentru scrape_multiple)",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="output",
                    description="Director sau fisier output",
                    type="string",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="timeout",
                    description="Timeout in secunde",
                    type="integer",
                    required=False,
                    default=30,
                ),
                ToolParameter(
                    name="headers",
                    description="Headers JSON pentru request",
                    type="string",
                    required=False,
                    default="",
                ),
            ],
            category="web",
            requires_confirmation=False,
        )

    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation", "")
        url = kwargs.get("url", "")
        html = kwargs.get("html", "")
        selector = kwargs.get("selector", "")
        urls = kwargs.get("urls", "")
        output = kwargs.get("output", "")
        timeout = int(kwargs.get("timeout", 30))
        headers_str = kwargs.get("headers", "")

        if not self._requests_available:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Library 'requests' not installed. Run: pip install requests"
            )

        operations = {
            "fetch": self._fetch,
            "parse": self._parse,
            "extract_links": self._extract_links,
            "extract_text": self._extract_text,
            "extract_images": self._extract_images,
            "scrape_multiple": self._scrape_multiple,
            "download": self._download,
            "extract_metadata": self._extract_metadata,
            "extract_forms": self._extract_forms,
        }

        if operation not in operations:
            return ToolResult(status=ToolStatus.ERROR, error=f"Operatie necunoscuta: {operation}")

        if operation not in ["parse"] and not url and not urls:
            return ToolResult(status=ToolStatus.ERROR, error="URL este obligatoriu")

        try:
            headers = {}
            if headers_str:
                try:
                    import json
                    headers = json.loads(headers_str)
                except Exception:
                    pass

            return operations[operation](url, html, selector, urls, output, timeout, headers, kwargs)
        except Exception as e:
            logger.error(f"Web scraper error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def _fetch(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Fetch continut de la URL."""
        try:
            import requests

            default_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            default_headers.update(headers)

            response = requests.get(url, headers=default_headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            is_binary = any(x in content_type for x in ["image", "pdf", "zip", "octet"])

            result = {
                "url": url,
                "status_code": response.status_code,
                "content_type": content_type,
                "headers": dict(response.headers),
                "final_url": response.url,
            }

            if is_binary:
                result["size"] = len(response.content)
                result["binary"] = True
            else:
                result["content"] = response.text
                result["size"] = len(response.text)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result,
                message=f"Fetched {url} ({response.status_code})"
            )
        except ImportError:
            return ToolResult(status=ToolStatus.ERROR, error="pip install requests")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Fetch failed: {e}")

    def _parse(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Parseaza HTML cu BeautifulSoup."""
        if not html:
            return ToolResult(status=ToolStatus.ERROR, error="HTML content este necesar")

        if not self._bs4_available:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Library 'beautifulsoup4' not installed. Run: pip install beautifulsoup4"
            )

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            if selector:
                elements = soup.select(selector)
                results = []
                for elem in elements:
                    results.append({
                        "tag": elem.name,
                        "text": elem.get_text(strip=True),
                        "html": str(elem),
                        "attrs": dict(elem.attrs)
                    })
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "count": len(results),
                        "elements": results
                    },
                    message=f"Gasite {len(results)} elemente"
                )
            else:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "title": soup.title.string if soup.title else "",
                        "text": soup.get_text()[:1000],
                        "soup": str(soup)[:500]
                    },
                    message="HTML parsed"
                )
        except ImportError:
            return ToolResult(status=ToolStatus.ERROR, error="pip install beautifulsoup4")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Parse failed: {e}")

    def _extract_links(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Extrage toate linkurile din pagina."""
        if not html:
            # Fetch first
            fetch_result = self._fetch(url, "", "", "", "", timeout, headers, kwargs)
            if not fetch_result.is_success:
                return fetch_result
            html = fetch_result.data.get("content", "")

        if not self._bs4_available:
            # Fallback to regex
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"count": len(links), "links": links},
                message=f"Gasite {len(links)} linkuri (regex mode)"
            )

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            links_data = []

            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(url, href) if url else href
                
                links_data.append({
                    "text": a.get_text(strip=True),
                    "href": href,
                    "full_url": full_url,
                    "domain": urlparse(full_url).netloc if full_url.startswith("http") else ""
                })

            # Filter by selector if provided
            if selector:
                links_data = [l for l in links_data if selector.lower() in l["href"].lower()]

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "count": len(links_data),
                    "links": links_data[:100]
                },
                message=f"Gasite {len(links_data)} linkuri"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Extract links failed: {e}")

    def _extract_text(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Extrage textul din pagina."""
        if not html:
            fetch_result = self._fetch(url, "", "", "", "", timeout, headers, kwargs)
            if not fetch_result.is_success:
                return fetch_result
            html = fetch_result.data.get("content", "")

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            text = soup.get_text(separator="\n", strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "text": text[:5000],
                    "length": len(text)
                },
                message=f"Extras {len(text)} caractere text"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Extract text failed: {e}")

    def _extract_images(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Extrage URL-urile imaginilor."""
        if not html:
            fetch_result = self._fetch(url, "", "", "", "", timeout, headers, kwargs)
            if not fetch_result.is_success:
                return fetch_result
            html = fetch_result.data.get("content", "")

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            images = []

            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src", "")
                if src:
                    images.append({
                        "src": urljoin(url, src) if url else src,
                        "alt": img.get("alt", ""),
                        "width": img.get("width", ""),
                        "height": img.get("height", "")
                    })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "count": len(images),
                    "images": images
                },
                message=f"Gasite {len(images)} imagini"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Extract images failed: {e}")

    def _scrape_multiple(self, url: str, html: str, selector: str, urls_str: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Scrapeaza mai multe URL-uri."""
        if not urls_str:
            return ToolResult(status=ToolStatus.ERROR, error="Lista de URL-uri este necesara")

        try:
            import json
            urls_list = json.loads(urls_str)
        except Exception:
            # Try splitting by comma or newline
            urls_list = re.split(r'[,\n]', urls_str)
            urls_list = [u.strip() for u in urls_list if u.strip()]

        if not urls_list:
            return ToolResult(status=ToolStatus.ERROR, error="Nu s-au gasit URL-uri valide")

        results = []
        for url_item in urls_list[:20]:  # Limit to 20
            fetch_result = self._fetch(url_item, "", "", "", "", timeout, headers, kwargs)
            results.append({
                "url": url_item,
                "success": fetch_result.is_success,
                "status_code": fetch_result.data.get("status_code") if fetch_result.is_success else None,
                "error": fetch_result.error if not fetch_result.is_success else None,
                "size": fetch_result.data.get("size") if fetch_result.is_success else None
            })

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "total": len(results),
                "successful": sum(1 for r in results if r["success"]),
                "failed": sum(1 for r in results if not r["success"]),
                "results": results
            },
            message=f"Scraped {sum(1 for r in results if r['success'])}/{len(results)} URLs"
        )

    def _download(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Descarca fisier de la URL."""
        if not output:
            # Generate filename from URL
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "download"
            if not filename or "." not in filename:
                filename = "download_" + str(hash(url))[:8]
            output = filename

        try:
            import requests

            # Create directory if needed
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            default_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            default_headers.update(headers)

            response = requests.get(url, headers=default_headers, timeout=timeout, stream=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            size = output_path.stat().st_size

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "file": str(output_path),
                    "size": size,
                    "size_mb": round(size / (1024 * 1024), 2)
                },
                message=f"Downloaded: {output_path.name} ({round(size / 1024, 1)} KB)"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Download failed: {e}")

    def _extract_metadata(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Extrage metadata din pagina (title, description, og tags)."""
        if not html:
            fetch_result = self._fetch(url, "", "", "", "", timeout, headers, kwargs)
            if not fetch_result.is_success:
                return fetch_result
            html = fetch_result.data.get("content", "")

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            metadata = {
                "title": "",
                "description": "",
                "keywords": "",
                "og_tags": {},
                "meta_tags": {}
            }

            # Title
            if soup.title:
                metadata["title"] = soup.title.string or ""

            # Meta tags
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property", "")
                content = meta.get("content", "")
                
                if not name or not content:
                    continue

                name = name.lower()
                if name in ["description", "keywords", "author"]:
                    metadata[name] = content
                elif name.startswith("og:"):
                    metadata["og_tags"][name] = content
                elif name.startswith("twitter:"):
                    metadata["meta_tags"][name] = content

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=metadata,
                message="Metadata extras"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Extract metadata failed: {e}")

    def _extract_forms(self, url: str, html: str, selector: str, urls: str, output: str, timeout: int, headers: Dict, kwargs: Dict) -> ToolResult:
        """Extrage formularele din pagina."""
        if not html:
            fetch_result = self._fetch(url, "", "", "", "", timeout, headers, kwargs)
            if not fetch_result.is_success:
                return fetch_result
            html = fetch_result.data.get("content", "")

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            forms = []

            for form in soup.find_all("form"):
                form_data = {
                    "action": urljoin(url, form.get("action", "")) if url else form.get("action", ""),
                    "method": form.get("method", "get").upper(),
                    "inputs": []
                }

                for input_tag in form.find_all(["input", "textarea", "select"]):
                    form_data["inputs"].append({
                        "name": input_tag.get("name", ""),
                        "type": input_tag.get("type", "text"),
                        "tag": input_tag.name,
                        "placeholder": input_tag.get("placeholder", "")
                    })

                forms.append(form_data)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "count": len(forms),
                    "forms": forms
                },
                message=f"Gasite {len(forms)} formulare"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Extract forms failed: {e}")


def smoke_test():
    """Smoke test pentru Web Scraper tool."""
    print("[*] Testing Web Scraper Tool...")
    
    tool = WebScraperTool()
    
    # Check libraries
    print(f"[*] requests: {'Available' if tool._requests_available else 'NOT INSTALLED'}")
    print(f"[*] beautifulsoup4: {'Available' if tool._bs4_available else 'NOT INSTALLED'}")
    
    if not tool._requests_available:
        print("[!] Install with: pip install requests beautifulsoup4")
        return
    
    # Test fetch
    result = tool.execute(operation="fetch", url="https://httpbin.org/html")
    if result.is_success:
        print(f"[OK] Fetch: {result.data.get('status_code')} - {len(result.data.get('content', ''))} chars")
    else:
        print(f"[!] Fetch: {result.error}")
    
    print("[*] Web Scraper smoke test complete")


if __name__ == "__main__":
    smoke_test()