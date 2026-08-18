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
    "opencode-go": SourceEntry("opencode-go", "OpenCode Go", "app.sources.opencode", 120, priority=1),
    "opencode-zen": SourceEntry("opencode-zen", "OpenCode Zen", "app.sources.opencode_zen", 240, priority=1),
    "nous-portal": SourceEntry("nous-portal", "Nous Portal", "app.sources.nous", 120, priority=1),
    "openrouter-models": SourceEntry("openrouter-models", "OpenRouter", "app.sources.openrouter", 360, priority=2),
    "models-dev": SourceEntry("models-dev", "models.dev", "app.sources.models_dev", 1440, priority=3),
    "artificial-analysis": SourceEntry("artificial-analysis", "Artificial Analysis", "app.sources.artificial_analysis", 1440, priority=3),
    "hf-router": SourceEntry("hf-router", "HuggingFace Router", "app.sources.hf_router", 1440, priority=3),
    "vercel-changelog": SourceEntry("vercel-changelog", "Vercel Changelog", "app.sources.vercel", 120, priority=2),
    "rss-feeds": SourceEntry("rss-feeds", "RSS Feeds", "app.sources.rss", 120, priority=2),
    "hackernews": SourceEntry("hackernews", "Hacker News", "app.sources.hackernews", 120, priority=2),
    # International providers
    "sensenova": SourceEntry("sensenova", "SenseNova", "app.sources.sensenova", 240, priority=1),
    "sakura-ai": SourceEntry("sakura-ai", "Sakura AI", "app.sources.sakura", 1440, priority=2),
    "scaleway": SourceEntry("scaleway", "Scaleway", "app.sources.scaleway", 1440, priority=2),
    "ovhcloud": SourceEntry("ovhcloud", "OVHcloud", "app.sources.ovhcloud", 1440, priority=2),
    "zai": SourceEntry("zai", "Z.AI", "app.sources.zai", 240, priority=1),
    "alibaba": SourceEntry("alibaba", "Alibaba Bailian", "app.sources.alibaba", 1440, priority=2),
    "akashml": SourceEntry("akashml", "AkashML", "app.sources.akashml", 1440, priority=2),
    # Additional providers from specs
    "perplexity": SourceEntry("perplexity", "Perplexity", "app.sources.perplexity", 1440, priority=2),
    "upstage": SourceEntry("upstage", "Upstage", "app.sources.upstage", 1440, priority=2),
    "siliconflow": SourceEntry("siliconflow", "SiliconFlow", "app.sources.siliconflow", 1440, priority=2),
    "xiaomi": SourceEntry("xiaomi", "Xiaomi MiMo", "app.sources.xiaomi", 1440, priority=2),
    "minimax": SourceEntry("minimax", "MiniMax", "app.sources.minimax", 1440, priority=2),
    "baidu": SourceEntry("baidu", "Baidu Qianfan", "app.sources.baidu", 1440, priority=2),
    "tencent": SourceEntry("tencent", "Tencent TokenHub", "app.sources.tencent", 1440, priority=2),
    "moonshot": SourceEntry("moonshot", "Moonshot/Kimi", "app.sources.moonshot", 1440, priority=2),
    "infini": SourceEntry("infini", "Infini-AI", "app.sources.infini", 1440, priority=3),
    "aion": SourceEntry("aion", "Aion Labs", "app.sources.aion", 1440, priority=2),
    "maritaca": SourceEntry("maritaca", "Maritaca", "app.sources.maritaca", 1440, priority=2),
    "sarvam": SourceEntry("sarvam", "Sarvam", "app.sources.sarvam", 1440, priority=3),
    "typhoon": SourceEntry("typhoon", "Typhoon", "app.sources.typhoon", 1440, priority=3),
    "nvidia": SourceEntry("nvidia", "NVIDIA NIM", "app.sources.nvidia", 1440, priority=2),
    "kilo": SourceEntry("kilo", "Kilo Gateway", "app.sources.kilo", 1440, priority=2),
    "chutes": SourceEntry("chutes", "Chutes", "app.sources.chutes", 1440, priority=3),
    "aethir": SourceEntry("aethir", "Aethir", "app.sources.aethir", 1440, priority=3),
    "nosana": SourceEntry("nosana", "Nosana", "app.sources.nosana", 1440, priority=3),
    "nebius": SourceEntry("nebius", "Nebius", "app.sources.nebius", 1440, priority=3),
    "novita": SourceEntry("novita", "Novita", "app.sources.novita", 1440, priority=2),
    "io-net": SourceEntry("io-net", "io.net", "app.sources.io_net", 1440, priority=3),
    # Cloned repo sources
    "awesome-free-llm-apis": SourceEntry("awesome-free-llm-apis", "awesome-free-llm-apis", "app.sources.free_llm_apis", 1440, priority=1),
    "litellm-prices": SourceEntry("litellm-prices", "litellm prices", "app.sources.litellm_prices", 1440, priority=2),
    "context-engineering": SourceEntry("context-engineering", "Context Engineering", "app.sources.context_engineering", 1440, priority=3),
    "mcp-registry": SourceEntry("mcp-registry", "MCP Registry", "app.sources.mcp_registry", 1440, priority=2),
    "price-performance": SourceEntry("price-performance", "Price-Performance Dataset", "app.sources.price_performance", 1440, priority=2),
    "genai-prices": SourceEntry("genai-prices", "GenAI Prices", "app.sources.genai_prices", 1440, priority=2),
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
