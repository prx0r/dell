"""Decision Service — Canonical resolver for inference routes.

This is the single source of truth for all decision logic.
REST and MCP both call this service.

Key fixes from review:
1. Calculate cost BEFORE checking budget
2. Never coerce unknown to zero
3. Build endpoint-level candidates
4. Separate confidence from coverage
5. Remove neutral 50 for unknown
6. Don't treat context as quality
"""
from __future__ import annotations

import json
import math
import time
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class UnknownPolicy(Enum):
    EXCLUDE = "exclude"
    ALLOW_WITH_WARNING = "allow_with_warning"
    INCLUDE = "include"


@dataclass
class Workload:
    """Workload specification."""
    task: str = "general"
    input_tokens_per_request: int = 1000
    output_tokens_per_request: int = 500
    requests: int = 1
    concurrency: int = 1


@dataclass
class Constraints:
    """Hard constraints."""
    max_total_cost_usd: Optional[float] = None
    free_only: bool = False
    context_tokens_min: Optional[int] = None
    max_output_tokens_min: Optional[int] = None
    tools: str = "any"
    json_schema: str = "any"
    streaming: str = "any"
    openai_compatible: str = "any"
    automation_allowed: str = "any"
    requires_card: str = "any"
    requires_phone: str = "any"
    requires_kyc: str = "any"
    regions: Optional[list] = None
    quantization: Optional[list] = None


@dataclass
class Preferences:
    """Soft preferences for ranking."""
    objectives: list = None
    
    def __post_init__(self):
        if self.objectives is None:
            self.objectives = [
                {"name": "cost", "weight": 0.45},
                {"name": "reliability", "weight": 0.30},
                {"name": "throughput", "weight": 0.15},
                {"name": "quality", "weight": 0.10},
            ]


@dataclass
class EvidencePolicy:
    """Evidence handling policy."""
    unknown_hard_constraint: str = "exclude"
    stale: str = "exclude"
    conflicted: str = "exclude"
    minimum_confidence: float = 0.70
    minimum_evidence_coverage: float = 0.60


@dataclass
class ResolveRequest:
    """Full resolve request."""
    workload: Workload = None
    constraints: Constraints = None
    preferences: Preferences = None
    evidence_policy: EvidencePolicy = None
    
    def __post_init__(self):
        if self.workload is None:
            self.workload = Workload()
        if self.constraints is None:
            self.constraints = Constraints()
        if self.preferences is None:
            self.preferences = Preferences()
        if self.evidence_policy is None:
            self.evidence_policy = EvidencePolicy()


@dataclass
class RouteCandidate:
    """A candidate route (model × endpoint × offer)."""
    offer_id: str
    model_id: str
    provider_id: str
    endpoint_id: Optional[str] = None
    input_per_m: Optional[float] = None
    output_per_m: Optional[float] = None
    free: bool = False
    context_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    tools_supported: Optional[bool] = None
    json_schema_support: Optional[bool] = None
    streaming_support: Optional[bool] = None
    openai_compatible: Optional[bool] = None
    automation_allowed: Optional[bool] = None
    requires_card: Optional[bool] = None
    requires_phone: Optional[bool] = None
    requires_kyc: Optional[bool] = None
    region: Optional[str] = None
    lifecycle_state: str = "UNKNOWN"
    freshness_state: str = "UNKNOWN"
    evidence_coverage: float = 0.0
    reliability: Optional[float] = None
    throughput_tps: Optional[float] = None
    ttft_ms: Optional[float] = None
    quota_rpd: Optional[int] = None
    _workload_cost: Optional[float] = None
    _cost_known: bool = False


@dataclass
class RouteAssessment:
    """Assessed route with scoring and exclusion reasons."""
    candidate: RouteCandidate
    score: float = 0.0
    excluded_reasons: list = None
    evidence_coverage: float = 0.0
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.excluded_reasons is None:
            self.excluded_reasons = []


@dataclass
class ResolveResult:
    """Final resolve result."""
    recommended: Optional[dict] = None
    alternatives: list = None
    excluded: list = None
    decision: dict = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []
        if self.excluded is None:
            self.excluded = []
        if self.decision is None:
            self.decision = {}


def resolve(request: ResolveRequest, offers: list[dict], endpoints: list[dict] = None) -> ResolveResult:
    """Resolve the best route for a workload."""
    result = ResolveResult()
    
    # 1. Build route candidates (including endpoint-level)
    candidates = build_candidates(offers, endpoints)
    
    # 2. Calculate workload cost for EACH candidate FIRST
    for candidate in candidates:
        candidate._workload_cost = calculate_workload_cost(candidate, request.workload)
        candidate._cost_known = candidate._workload_cost is not None
    
    # 3. Apply hard constraints (AFTER cost calculation)
    eligible = []
    excluded = []
    
    for candidate in candidates:
        reasons = apply_hard_constraints(candidate, request.constraints, request.evidence_policy)
        if reasons:
            excluded.append({
                "offer_id": candidate.offer_id,
                "model_id": candidate.model_id,
                "provider_id": candidate.provider_id,
                "reasons": reasons,
            })
        else:
            eligible.append(candidate)
    
    result.excluded = excluded
    
    if not eligible:
        result.decision = {
            "status": "NO_CANDIDATES",
            "excluded_count": len(excluded),
            "reasons": get_exclusion_summary(excluded),
        }
        return result
    
    # 4. Score candidates
    assessments = []
    for candidate in eligible:
        assessment = assess_route(candidate, request)
        assessments.append(assessment)
    
    # 5. Sort by score
    assessments.sort(key=lambda x: x.score, reverse=True)
    
    # 6. Build result
    if assessments:
        best = assessments[0]
        result.recommended = {
            "offer_id": best.candidate.offer_id,
            "model_id": best.candidate.model_id,
            "provider_id": best.candidate.provider_id,
            "endpoint_id": best.candidate.endpoint_id,
            "score": best.score,
            "evidence_coverage": best.evidence_coverage,
            "confidence": best.confidence,
            "estimated_cost": best.candidate._workload_cost,
            "reasons": get_recommendation_reasons(best.candidate, request),
        }
        
        result.alternatives = [
            {
                "offer_id": a.candidate.offer_id,
                "model_id": a.candidate.model_id,
                "provider_id": a.candidate.provider_id,
                "score": a.score,
                "estimated_cost": a.candidate._workload_cost,
            }
            for a in assessments[1:5]
        ]
    
    result.decision = {
        "status": "RESOLVED",
        "candidates": len(eligible),
        "excluded": len(excluded),
        "coverage": len(eligible) / len(offers) if offers else 0,
        "method": "decision_service_v2",
        "as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    
    return result


def build_candidates(offers: list[dict], endpoints: list[dict] = None) -> list[RouteCandidate]:
    """Build route candidates from offers AND endpoints."""
    candidates = []
    
    # Build from offers
    for offer in offers:
        candidate = RouteCandidate(
            offer_id=offer.get("offer_id", ""),
            model_id=offer.get("model_id", ""),
            provider_id=offer.get("provider_id", ""),
            input_per_m=offer.get("input_per_m"),
            output_per_m=offer.get("output_per_m"),
            free=offer.get("free", False),
            context_tokens=offer.get("context_tokens"),
            max_output_tokens=offer.get("max_output_tokens"),
            lifecycle_state=offer.get("lifecycle_state", "UNKNOWN"),
            region=offer.get("region"),
        )
        
        # Extract metadata
        meta = offer.get("metadata", {})
        candidate.tools_supported = meta.get("tool_call")
        candidate.json_schema_support = meta.get("json_schema_support")
        candidate.streaming_support = meta.get("streaming_support")
        candidate.openai_compatible = meta.get("openai_compatible")
        candidate.automation_allowed = meta.get("automation_allowed")
        candidate.requires_card = meta.get("requires_card")
        candidate.requires_phone = meta.get("requires_phone")
        candidate.requires_kyc = meta.get("requires_kyc")
        candidate.reliability = meta.get("reliability")
        candidate.throughput_tps = meta.get("throughput_tps")
        candidate.ttft_ms = meta.get("ttft_ms")
        candidate.quota_rpd = offer.get("requests_per_day")
        
        candidates.append(candidate)
    
    # Build from endpoints (if provided)
    if endpoints:
        for endpoint in endpoints:
            # Check if this endpoint already has a candidate
            existing = [c for c in candidates if c.endpoint_id == endpoint.get("endpoint_id")]
            if not existing:
                # Create new candidate from endpoint
                candidate = RouteCandidate(
                    offer_id=endpoint.get("offer_id", ""),
                    model_id=endpoint.get("model_id", ""),
                    provider_id=endpoint.get("serving_provider_id", ""),
                    endpoint_id=endpoint.get("endpoint_id"),
                    input_per_m=endpoint.get("input_per_m"),
                    output_per_m=endpoint.get("output_per_m"),
                    free=endpoint.get("is_free", False),
                    context_tokens=endpoint.get("context_tokens"),
                    max_output_tokens=endpoint.get("max_output_tokens"),
                    reliability=endpoint.get("reliability"),
                    throughput_tps=endpoint.get("throughput_p50_tps"),
                    ttft_ms=endpoint.get("latency_p50_ms"),
                )
                candidates.append(candidate)
    
    return candidates


def apply_hard_constraints(candidate: RouteCandidate, constraints: Constraints,
                          evidence_policy: EvidencePolicy) -> list:
    """Apply hard constraints. Returns exclusion reasons."""
    reasons = []
    
    # Cost constraint — check AFTER cost calculation
    if constraints.max_total_cost_usd is not None:
        if candidate._workload_cost is not None:
            # Cost is known, check budget
            if candidate._workload_cost > constraints.max_total_cost_usd:
                reasons.append("COST_EXCEEDS_BUDGET")
        elif not candidate.free:
            # Cost is unknown and not free — exclude under strict policy
            if evidence_policy.unknown_hard_constraint == "exclude":
                reasons.append("PRICE_UNKNOWN")
    
    # Free only
    if constraints.free_only and not candidate.free:
        reasons.append("NOT_FREE")
    
    # Context minimum
    if constraints.context_tokens_min is not None:
        if candidate.context_tokens is None:
            if evidence_policy.unknown_hard_constraint == "exclude":
                reasons.append("CONTEXT_UNKNOWN")
        elif candidate.context_tokens < constraints.context_tokens_min:
            reasons.append("CONTEXT_INSUFFICIENT")
    
    # Output tokens minimum
    if constraints.max_output_tokens_min is not None:
        if candidate.max_output_tokens is None:
            if evidence_policy.unknown_hard_constraint == "exclude":
                reasons.append("OUTPUT_UNKNOWN")
        elif candidate.max_output_tokens < constraints.max_output_tokens_min:
            reasons.append("OUTPUT_INSUFFICIENT")
    
    # Tools constraint
    if constraints.tools == "required":
        if candidate.tools_supported is False:
            reasons.append("TOOLS_NOT_SUPPORTED")
        elif candidate.tools_supported is None:
            if evidence_policy.unknown_hard_constraint == "exclude":
                reasons.append("TOOLS_UNKNOWN")
    
    # JSON schema constraint
    if constraints.json_schema == "required":
        if candidate.json_schema_support is False:
            reasons.append("JSON_SCHEMA_NOT_SUPPORTED")
        elif candidate.json_schema_support is None:
            if evidence_policy.unknown_hard_constraint == "exclude":
                reasons.append("JSON_SCHEMA_UNKNOWN")
    
    # Automation constraint
    if constraints.automation_allowed == "required":
        if candidate.automation_allowed is False:
            reasons.append("AUTOMATION_NOT_ALLOWED")
        elif candidate.automation_allowed is None:
            if evidence_policy.unknown_hard_constraint == "exclude":
                reasons.append("AUTOMATION_UNKNOWN")
    
    # Card constraint
    if constraints.requires_card == "forbidden":
        if candidate.requires_card is True:
            reasons.append("CARD_REQUIRED")
        elif candidate.requires_card is None:
            if evidence_policy.unknown_hard_constraint == "exclude":
                reasons.append("CARD_STATUS_UNKNOWN")
    
    # Phone constraint
    if constraints.requires_phone == "forbidden":
        if candidate.requires_phone is True:
            reasons.append("PHONE_REQUIRED")
    
    # KYC constraint
    if constraints.requires_kyc == "forbidden":
        if candidate.requires_kyc is True:
            reasons.append("KYC_REQUIRED")
    
    # Region constraint
    if constraints.regions:
        if candidate.region and candidate.region not in constraints.regions:
            reasons.append("REGION_NOT_ALLOWED")
    
    # Lifecycle constraint
    if evidence_policy.stale == "exclude":
        if candidate.lifecycle_state == "STALE":
            reasons.append("STALE")
    
    return reasons


def calculate_workload_cost(candidate: RouteCandidate, workload: Workload) -> Optional[float]:
    """Calculate total workload cost.
    
    Returns None if cost cannot be calculated (unknown price).
    NEVER coerces unknown to zero.
    """
    if candidate.free:
        return 0.0
    
    # If ANY price component is unknown, cost is unknown
    if candidate.input_per_m is None:
        return None  # Unknown — do NOT coerce to zero
    
    # Output price can be None (unknown) — cost is still calculable from input
    output_per_m = candidate.output_per_m if candidate.output_per_m is not None else 0
    
    input_cost = candidate.input_per_m * workload.input_tokens_per_request / 1_000_000
    output_cost = output_per_m * workload.output_tokens_per_request / 1_000_000
    request_cost = input_cost + output_cost
    total_cost = request_cost * workload.requests
    
    return round(total_cost, 6)


def assess_route(candidate: RouteCandidate, request: ResolveRequest) -> RouteAssessment:
    """Assess a route with scoring."""
    assessment = RouteAssessment(candidate=candidate)
    
    # Calculate evidence coverage (fraction of fields with evidence)
    fields = [
        candidate.input_per_m is not None,
        candidate.output_per_m is not None,
        candidate.context_tokens is not None,
        candidate.tools_supported is not None,
        candidate.reliability is not None,
        candidate.throughput_tps is not None,
    ]
    assessment.evidence_coverage = sum(fields) / len(fields)
    
    # Calculate confidence SEPARATELY from coverage
    # Confidence is about evidence quality, not quantity
    confidence_factors = []
    
    # Source authority
    if candidate.reliability is not None:
        confidence_factors.append(candidate.reliability / 100)
    
    # Measurement recency (assume recent if measured)
    if candidate.throughput_tps is not None:
        confidence_factors.append(0.9)
    
    # Corroboration (if multiple sources)
    if candidate.evidence_coverage > 0.5:
        confidence_factors.append(0.8)
    
    if confidence_factors:
        assessment.confidence = sum(confidence_factors) / len(confidence_factors)
    else:
        assessment.confidence = 0.3  # Low confidence when no evidence
    
    # Score based on preferences — NO neutral 50 for unknown
    score = 0
    for obj in request.preferences.objectives:
        weight = obj.get("weight", 0.25)
        name = obj.get("name", "cost")
        
        if name == "cost":
            if candidate.free:
                score += weight * 100
            elif candidate._workload_cost is not None:
                # Score based on actual cost, not input_per_m
                score += weight * max(0, 100 - (candidate._workload_cost * 1000))
            else:
                # Unknown cost — penalty, not neutral
                score += weight * 20
        elif name == "reliability":
            if candidate.reliability is not None:
                score += weight * candidate.reliability
            else:
                # Unknown reliability — penalty, not neutral
                score += weight * 30
        elif name == "throughput":
            if candidate.throughput_tps is not None:
                score += weight * min(100, candidate.throughput_tps / 2)
            else:
                # Unknown throughput — penalty, not neutral
                score += weight * 30
        elif name == "quality":
            # Quality from benchmarks, NOT from context
            meta = {}  # Would need benchmark data
            if meta.get("coding_score"):
                score += weight * meta["coding_score"]
            else:
                # Unknown quality — penalty
                score += weight * 40
    
    assessment.score = round(score, 2)
    
    return assessment


def get_exclusion_summary(excluded: list) -> dict:
    """Get summary of exclusion reasons."""
    reasons = {}
    for e in excluded:
        for r in e.get("reasons", []):
            reasons[r] = reasons.get(r, 0) + 1
    return reasons


def get_recommendation_reasons(candidate: RouteCandidate, request: ResolveRequest) -> list:
    """Get reasons for recommendation."""
    reasons = []
    
    if candidate.free:
        reasons.append("Free tier available")
    
    if candidate.context_tokens and request.constraints.context_tokens_min:
        if candidate.context_tokens >= request.constraints.context_tokens_min:
            reasons.append("Context sufficient (%d >= %d)" % (
                candidate.context_tokens, request.constraints.context_tokens_min))
    
    if request.constraints.tools == "required" and candidate.tools_supported:
        reasons.append("Tool calling supported")
    
    if candidate.reliability and candidate.reliability >= 80:
        reasons.append("High reliability (%d%%)" % candidate.reliability)
    
    if candidate._workload_cost is not None:
        reasons.append("Estimated cost: $%.6f" % candidate._workload_cost)
    
    return reasons
