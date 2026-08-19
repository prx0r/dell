"""app/observations.py — Dell's observation model.

Dell maintains observations, not just deals. Every model/endpoint has:
- What's ADVERTISED (from litellm, awesome-free-llm-apis, etc.)
- What's OBSERVED (from probes, health checks, user reports)
- What's VERIFIED (from actual testing)
- CONSTRAINTS (rate limits, manual setup, regions)
- CONFIDENCE (how sure are we?)

States: LIVE, DEGRADED, FAILED_PROBE, STALE, UNKNOWN
Rule: NO RECENT PROBE != DEAD
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EndpointState(Enum):
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    FAILED_PROBE = "FAILED_PROBE"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass
class AdvertisedSpec:
    """What the provider claims."""
    cost_per_million_input: float | None = None
    cost_per_million_output: float | None = None
    context_window: int | None = None
    max_output: int | None = None
    tool_calling: bool = False
    structured_output: bool = False
    vision: bool = False
    reasoning: bool = False
    free_tier: bool = False
    rate_limit_rpm: int | None = None
    rate_limit_tpm: int | None = None
    regions: list[str] = field(default_factory=list)
    requires_signup: bool = False
    requires_manual_setup: bool = False


@dataclass
class ObservedSpec:
    """What we've actually measured."""
    last_probe_at: str | None = None
    success_rate_1h: float | None = None
    success_rate_24h: float | None = None
    median_ttft_ms: float | None = None
    median_tokens_per_sec: float | None = None
    p95_latency_ms: float | None = None
    rate_429_1h: float | None = None
    total_probes: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_error: str | None = None


@dataclass
class VerifiedSpec:
    """What we've actually tested."""
    basic_completion: str = "UNKNOWN"  # PASS, FAIL, UNKNOWN
    structured_output: str = "UNKNOWN"
    tool_calling: str = "UNKNOWN"
    context_32k: str = "UNKNOWN"
    context_64k: str = "UNKNOWN"
    coding_fixture_score: float | None = None
    verified_at: str | None = None


@dataclass
class Constraints:
    """Real-world constraints."""
    free: bool = False
    probable_rate_limit: int | None = None
    manual_account_setup: bool = False
    regions: list[str] = field(default_factory=list)
    requires_api_key: bool = True
    max_concurrent: int | None = None


@dataclass
class EndpointObservation:
    """Complete observation for a model/endpoint."""
    provider: str
    model: str
    advertised: AdvertisedSpec
    observed: ObservedSpec
    verified: VerifiedSpec
    constraints: Constraints
    confidence: float = 0.0
    state: EndpointState = EndpointState.UNKNOWN
    last_updated: str = ""
    source: str = ""

    @property
    def effective_cost(self) -> float | None:
        """Actual cost considering free tier and observed behavior."""
        if self.constraints.free:
            return 0.0
        return self.advertised.cost_per_million_input

    @property
    def is_obtainable(self) -> bool:
        """Can we actually use this right now?"""
        return self.state in (EndpointState.LIVE, EndpointState.DEGRADED)

    @property
    def reliability_score(self) -> float:
        """0-1 score based on observed success rates."""
        if self.observed.total_probes == 0:
            return 0.5  # unknown, not zero
        return self.observed.success_rate_24h or self.observed.success_rate_1h or 0.5


def create_observation(
    provider: str,
    model: str,
    advertised: AdvertisedSpec,
    source: str = "",
) -> EndpointObservation:
    """Create a new observation with UNKNOWN state."""
    return EndpointObservation(
        provider=provider,
        model=model,
        advertised=advertised,
        observed=ObservedSpec(),
        verified=VerifiedSpec(),
        constraints=Constraints(),
        state=EndpointState.UNKNOWN,
        source=source,
    )


def update_observation(
    obs: EndpointObservation,
    *,
    success: bool | None = None,
    latency_ms: float | None = None,
    ttft_ms: float | None = None,
    rate_429: bool = False,
    error: str | None = None,
) -> EndpointObservation:
    """Update observation with probe results."""
    now = datetime.now(timezone.utc).isoformat()
    obs.observed.last_probe_at = now
    obs.observed.total_probes += 1

    if success is not None:
        if success:
            obs.observed.total_successes += 1
        else:
            obs.observed.total_failures += 1

    if latency_ms is not None:
        obs.observed.p95_latency_ms = latency_ms

    if ttft_ms is not None:
        obs.observed.median_ttft_ms = ttft_ms

    if rate_429:
        obs.observed.rate_429_1h = (obs.observed.rate_429_1h or 0) + 0.1

    if error:
        obs.observed.last_error = error

    # Update success rates
    if obs.observed.total_probes > 0:
        obs.observed.success_rate_24h = obs.observed.total_successes / obs.observed.total_probes

    # Update state
    if obs.observed.total_probes == 0:
        obs.state = EndpointState.UNKNOWN
    elif obs.observed.success_rate_24h and obs.observed.success_rate_24h < 0.5:
        obs.state = EndpointState.FAILED_PROBE
    elif obs.observed.rate_429_1h and obs.observed.rate_429_1h > 0.3:
        obs.state = EndpointState.DEGRADED
    elif obs.observed.success_rate_24h and obs.observed.success_rate_24h >= 0.9:
        obs.state = EndpointState.LIVE
    else:
        obs.state = EndpointState.DEGRADED

    obs.last_updated = now
    return obs
