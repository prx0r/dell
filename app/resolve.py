"""Resolve Endpoint — Unified decision primitive.

Instead of users learning multiple endpoints, give them one:
POST /v1/resolve

Input:
{
  "workload": {...},
  "constraints": {...},
  "preferences": {...},
  "evidence_policy": {...}
}

Output:
{
  "recommended": {...},
  "alternatives": [...],
  "excluded": [...],
  "decision": {...}
}
"""
from __future__ import annotations

import json
from typing import Optional


class ResolveRequest:
    """Structured resolve request."""
    
    def __init__(self, workload: dict = None, constraints: dict = None,
                 preferences: dict = None, evidence_policy: dict = None):
        self.workload = workload or {}
        self.constraints = constraints or {}
        self.preferences = preferences or {}
        self.evidence_policy = evidence_policy or {"unknown": "exclude", "stale": "exclude"}
    
    def to_dict(self) -> dict:
        return {
            "workload": self.workload,
            "constraints": self.constraints,
            "preferences": self.preferences,
            "evidence_policy": self.evidence_policy,
        }


class ResolveResult:
    """Structured resolve result."""
    
    def __init__(self):
        self.recommended = None
        self.alternatives = []
        self.excluded = []
        self.decision = {}
    
    def to_dict(self) -> dict:
        return {
            "recommended": self.recommended,
            "alternatives": self.alternatives,
            "excluded": self.excluded,
            "decision": self.decision,
        }


def resolve(request: ResolveRequest, offers: list[dict]) -> ResolveResult:
    """Resolve the best route for a workload."""
    result = ResolveResult()
    
    # 1. Apply hard constraints
    candidates = []
    excluded = []
    
    for offer in offers:
        excluded_reasons = check_hard_constraints(offer, request.constraints, request.evidence_policy)
        if excluded_reasons:
            excluded.append({"offer_id": offer.get("offer_id"), "reasons": excluded_reasons})
        else:
            candidates.append(offer)
    
    result.excluded = excluded
    
    if not candidates:
        result.decision = {"status": "NO_CANDIDATES", "excluded_count": len(excluded)}
        return result
    
    # 2. Score candidates
    scored = []
    for offer in candidates:
        score = score_offer(offer, request.workload, request.preferences)
        scored.append({"offer": offer, "score": score})
    
    # 3. Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    # 4. Return recommendation
    if scored:
        best = scored[0]
        result.recommended = {
            "offer_id": best["offer"].get("offer_id"),
            "model_id": best["offer"].get("model_id"),
            "provider_id": best["offer"].get("provider_id"),
            "score": best["score"],
            "reasons": get_recommendation_reasons(best["offer"], request),
        }
        
        result.alternatives = [
            {
                "offer_id": s["offer"].get("offer_id"),
                "model_id": s["offer"].get("model_id"),
                "score": s["score"],
            }
            for s in scored[1:5]
        ]
    
    result.decision = {
        "status": "RESOLVED",
        "candidates": len(candidates),
        "excluded": len(excluded),
        "coverage": len(candidates) / len(offers) if offers else 0,
    }
    
    return result


def check_hard_constraints(offer: dict, constraints: dict, evidence_policy: dict) -> list:
    """Check hard constraints. Returns exclusion reasons."""
    reasons = []
    
    # Price constraint
    if constraints.get("max_cost_usd") is not None:
        if offer.get("input_per_m") is None and not offer.get("free"):
            reasons.append("PRICE_UNKNOWN")
    
    # Tool requirement
    if constraints.get("tools") == "required":
        meta = offer.get("metadata", {})
        if meta.get("tool_call") is False:
            reasons.append("TOOLS_NOT_SUPPORTED")
        elif meta.get("tool_call") is None and evidence_policy.get("unknown") == "exclude":
            reasons.append("TOOLS_UNKNOWN")
    
    # Context requirement
    if constraints.get("context_tokens", {}).get("min"):
        ctx = offer.get("context_tokens")
        min_ctx = constraints["context_tokens"]["min"]
        if ctx is None:
            reasons.append("CONTEXT_UNKNOWN")
        elif ctx < min_ctx:
            reasons.append("CONTEXT_INSUFFICIENT")
    
    # Free only
    if constraints.get("free_only") and not offer.get("free"):
        reasons.append("NOT_FREE")
    
    # Freshness
    if evidence_policy.get("stale") == "exclude":
        lifecycle = offer.get("lifecycle_state")
        if lifecycle == "STALE":
            reasons.append("STALE")
    
    return reasons


def score_offer(offer: dict, workload: dict, preferences: dict) -> float:
    """Score an offer for a workload."""
    score = 0
    
    # Cost score
    if offer.get("free"):
        score += 40
    elif offer.get("input_per_m") is not None:
        score += max(0, 40 - (offer["input_per_m"] * 10))
    
    # Quality score (from metadata)
    meta = offer.get("metadata", {})
    if meta.get("tool_call"):
        score += 20
    
    # Context score
    ctx = offer.get("context_tokens")
    if ctx and ctx >= 128000:
        score += 20
    elif ctx and ctx >= 32000:
        score += 10
    
    # Preference weighting
    if preferences.get("optimize") == "cost":
        score *= 1.5
    elif preferences.get("optimize") == "quality":
        score *= 1.2
    
    return min(100, score)


def get_recommendation_reasons(offer: dict, request: ResolveRequest) -> list:
    """Get reasons for recommendation."""
    reasons = []
    
    if offer.get("free"):
        reasons.append("Free tier available")
    
    if offer.get("context_tokens", 0) >= request.constraints.get("context_tokens", {}).get("min", 0):
        reasons.append("Context sufficient")
    
    meta = offer.get("metadata", {})
    if request.constraints.get("tools") == "required" and meta.get("tool_call"):
        reasons.append("Tool calling supported")
    
    return reasons
