"""app/claims.py — Dell's claim vs verification model.

PASSIVE INTELLIGENCE: what providers CLAIM
ACTIVE VERIFICATION: what Dell actually MEASURED

When a blog says "Provider X has Model Y free this month":
  CLAIM: Provider X says Model Y is free
  VERIFICATION: API request succeeded, $0 charged, tested at T

The verified live-resource graph is Dell's real product.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ClaimSource(Enum):
    PRICING_PAGE = "pricing_page"
    BLOG_POST = "blog_post"
    GITHUB_REPO = "github_repo"
    DISCORD = "discord"
    PROVIDER_DOCS = "provider_docs"
    NEWSLETTER = "newsletter"
    MODELS_DEV = "models.dev"
    LITELLM = "litellm"
    OPENROUTER = "openrouter"
    USER_REPORT = "user_report"


class VerificationStatus(Enum):
    UNVERIFIED = "UNVERIFIED"
    CLAIMED = "CLAIMED"
    PROBED = "PROBED"
    VERIFIED = "VERIFIED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STALE = "STALE"


@dataclass
class Claim:
    """What a provider CLAIMS about their offering."""
    claim_id: str
    provider: str
    model: str
    source: ClaimSource
    source_url: str
    claim_type: str  # "free", "pricing", "capability", "limit"
    claim_data: dict[str, Any]
    claimed_at: str
    confidence: float = 0.5  # how much we trust this source


@dataclass
class Verification:
    """What Dell actually MEASURED."""
    verification_id: str
    claim_id: str
    probe_type: str  # "completion", "latency", "tool_call", "json", "context", "rate_limit"
    probe_result: dict[str, Any]
    success: bool
    measured_at: str
    latency_ms: float | None = None
    cost_usd: float | None = None
    error: str | None = None


@dataclass
class VerifiedResource:
    """The VERIFIED state of a resource — what's actually obtainable."""
    provider: str
    model: str
    
    # From claims
    claimed_free: bool = False
    claimed_context: int | None = None
    claimed_capabilities: list[str] = field(default_factory=list)
    claim_source: str = ""
    claim_url: str = ""
    
    # From verification
    verified_state: VerificationState = VerificationStatus.UNVERIFIED
    last_probe_at: str | None = None
    probe_count: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    median_ttft_ms: float | None = None
    median_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    rate_429_1h: float = 0.0
    measured_cost_usd: float | None = None
    verified_capabilities: list[str] = field(default_factory=list)
    
    # Constraints
    free: bool = False
    requires_signup: bool = False
    manual_setup_required: bool = False
    regions: list[str] = field(default_factory=list)
    
    # Confidence
    confidence: float = 0.0
    evidence_count: int = 0


def create_claim(
    provider: str,
    model: str,
    source: ClaimSource,
    source_url: str,
    claim_type: str,
    claim_data: dict[str, Any],
    confidence: float = 0.5,
) -> Claim:
    """Create a new claim from passive intelligence."""
    return Claim(
        claim_id=f"claim_{uuid.uuid4().hex[:12]}",
        provider=provider,
        model=model,
        source=source,
        source_url=source_url,
        claim_type=claim_type,
        claim_data=claim_data,
        claimed_at=datetime.now(timezone.utc).isoformat(),
        confidence=confidence,
    )


def create_verification(
    claim_id: str,
    probe_type: str,
    probe_result: dict[str, Any],
    success: bool,
    latency_ms: float | None = None,
    cost_usd: float | None = None,
    error: str | None = None,
) -> Verification:
    """Create a verification record from active probing."""
    return Verification(
        verification_id=f"ver_{uuid.uuid4().hex[:12]}",
        claim_id=claim_id,
        probe_type=probe_type,
        probe_result=probe_result,
        success=success,
        measured_at=datetime.now(timezone.utc).isoformat(),
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        error=error,
    )


def build_verified_resource(
    claim: Claim,
    verifications: list[Verification],
) -> VerifiedResource:
    """Build verified resource state from claim + verifications."""
    # Compute verification stats
    total_probes = len(verifications)
    success_count = sum(1 for v in verifications if v.success)
    success_rate = success_count / total_probes if total_probes > 0 else 0
    
    # Compute latency stats
    latencies = [v.latency_ms for v in verifications if v.latency_ms is not None]
    median_latency = sorted(latencies)[len(latencies) // 2] if latencies else None
    
    # Determine state
    if total_probes == 0:
        state = VerificationStatus.UNVERIFIED
    elif success_rate >= 0.9:
        state = VerificationStatus.VERIFIED
    elif success_rate >= 0.5:
        state = VerificationStatus.DEGRADED
    else:
        state = VerificationStatus.FAILED
    
    # Check freshness
    if verifications:
        last_probe = max(v.measured_at for v in verifications)
        hours_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_probe)).total_seconds() / 3600
        if hours_since > 24:
            state = VerificationStatus.STALE
    
    # Extract verified capabilities
    verified_caps = []
    for v in verifications:
        if v.success and v.probe_type not in verified_caps:
            verified_caps.append(v.probe_type)
    
    return VerifiedResource(
        provider=claim.provider,
        model=claim.model,
        claimed_free=claim.claim_data.get("free", False),
        claimed_context=claim.claim_data.get("context"),
        claimed_capabilities=claim.claim_data.get("capabilities", []),
        claim_source=claim.source.value,
        claim_url=claim.source_url,
        verified_state=state,
        last_probe_at=max(v.measured_at for v in verifications) if verifications else None,
        probe_count=total_probes,
        success_count=success_count,
        success_rate=success_rate,
        median_ttft_ms=next((v.latency_ms for v in verifications if v.probe_type == "ttft" and v.success), None),
        median_latency_ms=median_latency,
        verified_capabilities=verified_caps,
        free=claim.claim_data.get("free", False),
        confidence=min(1.0, claim.confidence * (success_rate if total_probes > 0 else 0.5)),
        evidence_count=total_probes,
    )
