"""app/sources/registry.py — Declarative source registry.

Tracks all sources, their adapters, cadence, and last-fetch state.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class SourceEntry:
    source_id: str
    name: str
    adapter_module: str  # e.g. "app.sources.opencode"
    cadence_minutes: int
    priority: int = 1  # 1=highest
    enabled: bool = True
    last_fetch_at: float = 0
    consecutive_failures: int = 0


SOURCES: dict[str, SourceEntry] = {
    # HIGH VALUE - Keep (direct providers with unique data)
    "opencode-go": SourceEntry("opencode-go", "OpenCode Go", "app.sources.opencode", 120, priority=1),
    "opencode-zen": SourceEntry("opencode-zen", "OpenCode Zen", "app.sources.opencode_zen", 240, priority=1),
    "nous-portal": SourceEntry("nous-portal", "Nous Portal", "app.sources.nous", 120, priority=1),
    "sensenova": SourceEntry("sensenova", "SenseNova", "app.sources.sensenova", 240, priority=1),
    "zai": SourceEntry("zai", "Z.AI", "app.sources.zai", 240, priority=1),
    
    # HIGH VALUE - Aggregators (complementary data)
    "openrouter-models": SourceEntry("openrouter-models", "OpenRouter", "app.sources.openrouter", 360, priority=2),
    "hf-router": SourceEntry("hf-router", "HuggingFace Router", "app.sources.hf_router", 1440, priority=3),
    "artificial-analysis": SourceEntry("artificial-analysis", "Artificial Analysis", "app.sources.artificial_analysis", 1440, priority=3),
    "models-dev": SourceEntry("models-dev", "models.dev", "app.sources.models_dev", 1440, priority=3),
    
    # HIGH VALUE - Community/Signal sources
    "rss-feeds": SourceEntry("rss-feeds", "RSS Feeds", "app.sources.rss", 120, priority=2),
    "hackernews": SourceEntry("hackernews", "Hacker News", "app.sources.hackernews", 120, priority=2),
    "vercel-changelog": SourceEntry("vercel-changelog", "Vercel Changelog", "app.sources.vercel", 120, priority=2),
    
    # HIGH VALUE - Pricing databases
    "litellm-prices": SourceEntry("litellm-prices", "litellm prices", "app.sources.litellm_prices", 1440, priority=2),
    "price-performance": SourceEntry("price-performance", "Price-Performance Dataset", "app.sources.price_performance", 1440, priority=2),
    
    # HIGH VALUE - Community free tier lists (merged - keep mnfst)
    "mnfst-free-apis": SourceEntry("mnfst-free-apis", "mnfst awesome-free-llm-apis", "app.sources.mnfst_apis", 1440, priority=1),
    
    # HIGH VALUE - Decentralized compute
    "bittensor-subnets": SourceEntry("bittensor-subnets", "Bittensor Subnets", "app.sources.bittensor_subnets", 360, priority=1),
    
    # MEDIUM VALUE - International providers (keep unique ones)
    "alibaba": SourceEntry("alibaba", "Alibaba Bailian", "app.sources.alibaba", 1440, priority=2),
    "siliconflow": SourceEntry("siliconflow", "SiliconFlow", "app.sources.siliconflow", 1440, priority=2),
    "nvidia": SourceEntry("nvidia", "NVIDIA NIM", "app.sources.nvidia", 1440, priority=2),
    "novita": SourceEntry("novita", "Novita", "app.sources.novita", 1440, priority=2),
    
    # MEDIUM VALUE - Browser automation (replaces opencode-go if reliable)
    "ego-lite-browser": SourceEntry("ego-lite-browser", "ego-lite Browser", "app.sources.ego_lite", 240, priority=1),
    
    # LOW VALUE - Disabled (redundant or low quality)
    # "awesome-free-llm-apis": DISABLED - same URL as mnfst-free-apis
    # "genai-prices": DISABLED - only extraction patterns, no actual pricing
    # "context-engineering": DISABLED - not relevant to pricing
    # "new-providers": DISABLED - static config, never changes
    # "decentralized-compute": DISABLED - static config, never changes
    # "mcp-registry": DISABLED - MCP server catalog, not LLM pricing
    
    # LOW VALUE - Keep but low priority (signal sources)
    
    # DISABLED - Redundant or low quality (kept for reference)
    # "sakura-ai": DISABLED - covered by litellm
    # "scaleway": DISABLED - covered by litellm
    # "ovhcloud": DISABLED - covered by litellm
    # "akashml": DISABLED - covered by litellm
    # "perplexity": DISABLED - covered by litellm
    # "upstage": DISABLED - covered by litellm
    # "xiaomi": DISABLED - covered by litellm
    # "minimax": DISABLED - covered by litellm
    # "baidu": DISABLED - covered by litellm
    # "tencent": DISABLED - covered by litellm
    # "moonshot": DISABLED - covered by litellm
    # "infini": DISABLED - covered by litellm
    # "aion": DISABLED - covered by litellm
    # "maritaca": DISABLED - covered by litellm
    # "sarvam": DISABLED - covered by litellm
    # "typhoon": DISABLED - covered by litellm
    # "kilo": DISABLED - covered by litellm
    # "chutes": DISABLED - covered by litellm
    # "aethir": DISABLED - covered by litellm
    # "nosana": DISABLED - covered by litellm
    # "nebius": DISABLED - covered by litellm
    # "io-net": DISABLED - covered by litellm
}


def get_all_sources() -> list[SourceEntry]:
    return list(SOURCES.values())


def get_due_sources() -> list[SourceEntry]:
    """Return sources whose cadence has elapsed since last fetch."""
    now = time.time()
    due = []
    for src in SOURCES.values():
        if not src.enabled:
            continue
        elapsed = now - src.last_fetch_at
        if elapsed >= src.cadence_minutes * 60:
            due.append(src)
    due.sort(key=lambda s: s.priority)
    return due


def record_fetch(source_id: str, success: bool):
    """Update fetch timestamp and failure count."""
    src = SOURCES.get(source_id)
    if not src:
        return
    src.last_fetch_at = time.time()
    if success:
        src.consecutive_failures = 0
    else:
        src.consecutive_failures += 1
        if src.consecutive_failures >= 3:
            src.enabled = False  # auto-disable after 3 consecutive failures


def get_adapter(source_id: str):
    """Dynamically import and return the adapter module."""
    src = SOURCES.get(source_id)
    if not src:
        return None
    import importlib
    try:
        return importlib.import_module(src.adapter_module)
    except ImportError:
        return None
