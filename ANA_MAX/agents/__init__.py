"""ANA MAX agent layer."""

__all__ = [
    "AgentScheduler",
    "BrowserReconAgent",
    "LocalBrainAgent",
    "WebReconAgent",
    "WebScraperAgent",
]


def __getattr__(name: str):
    if name == "AgentScheduler":
        from .agent_scheduler import AgentScheduler

        return AgentScheduler
    if name == "BrowserReconAgent":
        from .browser_recon_agent import BrowserReconAgent

        return BrowserReconAgent
    if name == "LocalBrainAgent":
        from .local_brain_agent import LocalBrainAgent

        return LocalBrainAgent
    if name == "WebReconAgent":
        from .web_recon_agent import WebReconAgent

        return WebReconAgent
    if name == "WebScraperAgent":
        from .web_scraper_agent import WebScraperAgent

        return WebScraperAgent
    raise AttributeError(name)
