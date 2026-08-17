#!/usr/bin/env python3
"""app/capability_registry.py — the capability registry (providers as replaceable tools).

Implements the newbuild pattern: "Tools don't become truth. Their outputs become observations."

Each capability (model DB, quality scores, pricing) has multiple providers. When one fails,
the system hotswaps to the next. Every observation carries provenance (which provider, when,
what confidence).

Capabilities:
  model_db        — canonical model database (litellm, models.dev, openrouter, llm-prices)
  quality_scores  — benchmark quality (artificial-analysis, self-measured)
  pricing         — live pricing (provider APIs, cached catalogs)
  rate_limits     — rate limit data (free-apis, provider docs)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderHealth:
    """Health state for a capability provider."""
    name: str
    capability: str
    last_success: float | None = None
    last_failure: float | None = None
    consecutive_failures: int = 0
    total_calls: int = 0
    total_failures: int = 0
    avg_latency_ms: float | None = None
    status: str = "unknown"  # unknown | healthy | degraded | failed

    @property
    def is_usable(self) -> bool:
        """Can we still try this provider? Failed after 3 consecutive = skip."""
        return self.consecutive_failures < 3

    def record_success(self, latency_ms: float = 0):
        self.last_success = time.time()
        self.consecutive_failures = 0
        self.total_calls += 1
        self.status = "healthy"
        if self.avg_latency_ms is None:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = 0.8 * self.avg_latency_ms + 0.2 * latency_ms

    def record_failure(self):
        self.last_failure = time.time()
        self.consecutive_failures += 1
        self.total_failures += 1
        self.total_calls += 1
        if self.consecutive_failures >= 3:
            self.status = "failed"
        elif self.consecutive_failures >= 1:
            self.status = "degraded"


@dataclass
class Observation:
    """A provenance-carrying observation from a provider."""
    value: Any
    provider: str
    capability: str
    observed_at: float = field(default_factory=time.time)
    confidence: float = 1.0  # 0-1, how much we trust this observation
    metadata: dict = field(default_factory=dict)


class CapabilityRegistry:
    """Registry of capabilities and their providers.

    Usage:
        reg = CapabilityRegistry()
        reg.register_provider("model_db", "litellm", priority=1)
        reg.register_provider("model_db", "models.dev", priority=2)

        # Get the best available provider
        provider = reg.get_provider("model_db")

        # Record observations
        reg.record_observation("model_db", "litellm", value={...}, confidence=0.9)

        # Check health
        health = reg.health_status()
    """

    def __init__(self):
        self._providers: dict[str, list[dict]] = {}  # capability → [{name, priority}]
        self._health: dict[str, dict[str, ProviderHealth]] = {}  # capability → {provider: health}
        self._observations: dict[str, list[Observation]] = {}  # capability → [observations]
        self._init_defaults()

    def _init_defaults(self):
        """Register the default capability providers for dealradar."""
        # Model database providers (priority = lower number = try first)
        self.register_provider("model_db", "litellm", priority=1,
                               description="litellm model_prices_and_context_window.json (3000+ models)")
        self.register_provider("model_db", "models.dev", priority=2,
                               description="models.dev catalog (capabilities + modalities)")
        self.register_provider("model_db", "openrouter", priority=3,
                               description="OpenRouter API (live pricing + free tier)")
        self.register_provider("model_db", "llm-prices", priority=4,
                               description="llm-prices community dataset")
        self.register_provider("model_db", "free-apis", priority=5,
                               description="awesome-free-llm-apis (free tier discovery)")

        # Quality score providers
        self.register_provider("quality_scores", "artificial-analysis", priority=1,
                               description="Artificial Analysis API (measured benchmarks)")
        self.register_provider("quality_scores", "self-measured", priority=2,
                               description="Self-measured via SWE-Bench/GPQA runs")

        # Pricing providers
        self.register_provider("pricing", "litellm", priority=1,
                               description="litellm cached pricing")
        self.register_provider("pricing", "openrouter", priority=2,
                               description="OpenRouter live pricing")
        self.register_provider("pricing", "provider-api", priority=3,
                               description="Direct provider API probes")

        # Rate limit providers
        self.register_provider("rate_limits", "free-apis", priority=1,
                               description="awesome-free-llm-apis rate limit data")
        self.register_provider("rate_limits", "provider-docs", priority=2,
                               description="Provider documentation")
        self.register_provider("rate_limits", "canary", priority=3,
                               description="Live canary probes")

    def register_provider(self, capability: str, name: str, priority: int = 10,
                          description: str = ""):
        """Register a provider for a capability."""
        if capability not in self._providers:
            self._providers[capability] = []
            self._health[capability] = {}

        # Upsert
        existing = [p for p in self._providers[capability] if p["name"] == name]
        if existing:
            existing[0]["priority"] = priority
            existing[0]["description"] = description
        else:
            self._providers[capability].append({
                "name": name, "priority": priority, "description": description
            })

        if name not in self._health[capability]:
            self._health[capability][name] = ProviderHealth(name=name, capability=capability)

        # Sort by priority
        self._providers[capability].sort(key=lambda p: p["priority"])

    def get_provider(self, capability: str) -> str | None:
        """Get the best available (healthy) provider for a capability."""
        if capability not in self._providers:
            return None
        for p in self._providers[capability]:
            health = self._health[capability].get(p["name"])
            if health and health.is_usable:
                return p["name"]
        return None

    def get_all_providers(self, capability: str) -> list[str]:
        """Get all providers for a capability, healthy or not."""
        if capability not in self._providers:
            return []
        return [p["name"] for p in self._providers[capability]]

    def record_success(self, capability: str, provider: str, latency_ms: float = 0):
        """Record a successful call to a provider."""
        if capability in self._health and provider in self._health[capability]:
            self._health[capability][provider].record_success(latency_ms)

    def record_failure(self, capability: str, provider: str):
        """Record a failed call to a provider."""
        if capability in self._health and provider in self._health[capability]:
            self._health[capability][provider].record_failure()

    def record_observation(self, capability: str, provider: str, value: Any,
                           confidence: float = 1.0, metadata: dict | None = None):
        """Record a provenance-carrying observation."""
        if capability not in self._observations:
            self._observations[capability] = []
        self._observations[capability].append(Observation(
            value=value, provider=provider, capability=capability,
            confidence=confidence, metadata=metadata or {}
        ))

    def health_status(self) -> dict:
        """Return health status for all capabilities and providers."""
        status = {}
        for cap, providers in self._health.items():
            status[cap] = {}
            for name, health in providers.items():
                status[cap][name] = {
                    "status": health.status,
                    "consecutive_failures": health.consecutive_failures,
                    "total_calls": health.total_calls,
                    "total_failures": health.total_failures,
                    "avg_latency_ms": round(health.avg_latency_ms, 1) if health.avg_latency_ms else None,
                    "last_success": health.last_success,
                    "last_failure": health.last_failure,
                    "is_usable": health.is_usable,
                }
        return status

    def capability_summary(self) -> dict:
        """Summary of all capabilities and their best provider."""
        summary = {}
        for cap in self._providers:
            best = self.get_provider(cap)
            all_p = self.get_all_providers(cap)
            healthy = [p for p in all_p
                       if self._health[cap][p].is_usable] if cap in self._health else []
            summary[cap] = {
                "best_provider": best,
                "total_providers": len(all_p),
                "healthy_providers": len(healthy),
                "providers": all_p,
            }
        return summary


# Singleton
_registry: CapabilityRegistry | None = None


def get_registry() -> CapabilityRegistry:
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry
