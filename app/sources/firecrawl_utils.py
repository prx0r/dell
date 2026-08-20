"""app/sources/firecrawl_utils.py — Firecrawl integration utilities.

Firecrawl is used for bulk scraping of JS-rendered provider pricing pages.
It's not a standalone source adapter — it's a utility that other adapters
can use when they need JS rendering at scale.

Usage:
    from .firecrawl_utils import firecrawl_scrape, firecrawl_search

Requires: FIRECRAWL_API_KEY environment variable (or self-hosted instance).
"""
from __future__ import annotations

import json
import os
import urllib.request

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"
FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY", "")


def firecrawl_scrape(url: str, formats: list[str] | None = None) -> dict | None:
    """Scrape a single URL via Firecrawl. Returns markdown + structured data.
    
    Args:
        url: URL to scrape
        formats: Output formats (default: ["markdown", "html"])
    
    Returns:
        Dict with 'markdown' and 'html' keys, or None on failure.
    """
    if not FIRECRAWL_KEY:
        return None
    
    payload = json.dumps({
        "url": url,
        "formats": formats or ["markdown", "html"],
        "onlyMainContent": True,
    }).encode()
    
    try:
        req = urllib.request.Request(
            f"{FIRECRAWL_BASE}/scrape",
            data=payload,
            headers={
                "Authorization": f"Bearer {FIRECRAWL_KEY}",
                "Content-Type": "application/json",
            }
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        return data.get("data", {})
    except Exception:
        return None


def firecrawl_search(query: str, limit: int = 10) -> list[dict]:
    """Search the web via Firecrawl. Returns list of {url, title, markdown}.
    
    Args:
        query: Search query
        limit: Max results
    
    Returns:
        List of search result dicts.
    """
    if not FIRECRAWL_KEY:
        return []
    
    payload = json.dumps({
        "query": query,
        "limit": limit,
        "scrapeOptions": {"formats": ["markdown"]},
    }).encode()
    
    try:
        req = urllib.request.Request(
            f"{FIRECRAWL_BASE}/search",
            data=payload,
            headers={
                "Authorization": f"Bearer {FIRECRAWL_KEY}",
                "Content-Type": "application/json",
            }
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        return data.get("data", [])
    except Exception:
        return []


def firecrawl_map(url: str, limit: int = 100) -> list[str]:
    """Map a website via Firecrawl. Returns list of discovered URLs.
    
    Useful for discovering all pricing pages on a provider's site.
    """
    if not FIRECRAWL_KEY:
        return []
    
    payload = json.dumps({
        "url": url,
        "limit": limit,
        "scrapeOptions": {"formats": ["markdown"]},
    }).encode()
    
    try:
        req = urllib.request.Request(
            f"{FIRECRAWL_BASE}/map",
            data=payload,
            headers={
                "Authorization": f"Bearer {FIRECRAWL_KEY}",
                "Content-Type": "application/json",
            }
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        return [r.get("url", "") for r in data.get("data", [])]
    except Exception:
        return []


# Quick provider pricing scrape targets
PRICING_PAGES = [
    "https://openrouter.ai/models",
    "https://huggingface.co/pricing",
    "https://groq.com/pricing",
    "https://www.together.ai/pricing",
    "https://fireworks.ai/pricing",
    "https://deepinfra.com/pricing",
    "https://www.novita.ai/pricing",
    "https://cloud.sambanova.ai/apis",
    "https://siliconflow.cn/pricing",
    "https://www.anthropic.com/pricing",
    "https://openai.com/pricing",
]
