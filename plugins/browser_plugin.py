"""
Browser Plugin for A.N.A.
=========================
Allows fetching the content of a specific web page.
"""

import requests
from plugins import Plugin, PluginMetadata
from typing import List, Callable, Optional


class BrowserPlugin(Plugin):
    """Plugin: Browser Access"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="browser_plugin",
            version="1.0.0",
            description="Allows fetching the content of a specific URL",
            author="Antigravity",
            capabilities=["web_fetch"]
        )
    
    def initialize(self) -> bool:
        return True
    
    def get_tools(self) -> List[Callable]:
        return [self.fetch_page]
    
    def fetch_page(self, url: str) -> str:
        """
        Fetches the content of a web page.
        
        Args:
            url: The URL of the page to fetch
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Simple text extraction (heuristic)
            content = response.text
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
                
            return f"Content of {url}:\n\n{content}"
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"
    
    def cleanup(self) -> None:
        pass
