"""Scoring V2 — One canonical implementation.

Based on research:
- LLMRouterBench: model suitability is task-dependent
- OpenRouter: separate price/throughput/latency/capabilities
- HELMET: long-context needs evaluation, not just advertised size

Core principle: geometric mean with evidence penalty.
"""
from __future__ import annotations

import json
import math
from typing import Optional


# Badge definitions with semantic tests
BADGES = {
    "free": {
        "description": "Zero-price or allowance mechanism explicitly known",
        "test": lambda v, o: o.get("free") is True,
    },
    "promo": {
        "description": "Temporary economic improvement",
        "test": lambda v, o: (o.get("usage_multiplier") or 0) > 1,
    },
    "high_value": {
        "description": "Good quality/cost frontier for stated workload",
        "test": lambda v, o: v.get("value", 0) >= 80,
    },
    "workhorse": {
        "description": "Broad sustained workload fitness",
        "test": lambda v, o: v.get("workhorse", 0) >= 70,
    },
    "fast_output": {
        "description": "High measured TPS",
        "test": lambda v, o: v.get("throughput_tps") and v["throughput_tps"] >= 50,
    },
    "low_latency": {
        "description": "Low measured TTFT",
        "test": lambda v, o: v.get("ttft_ms") and v["ttft_ms"] <= 200,
    },
    "long_context": {
        "description": "Large advertised context",
        "test": lambda v, o: (o.get("context_tokens") or 0) >= 128000,
    },
    "tool_capable": {
        "description": "Supports tools (measured or asserted)",
        "test": lambda v, o: v.get("tools_supported") == "measured" or 
                             (v.get("tools_supported") == "asserted" and v.get("tools_success_rate") is None),
    },
    "tool_proven": {
        "description": "Measured tool success",
        "test": lambda v, o: v.get("tools_success_rate") and v["tools_success_rate"] >= 0.8,
    },
    "coding_strong": {
        "description": "Coding benchmark evidence",
        "test": lambda v, o: v.get("coding_score") and v["coding_score"] >= 70,
    },
    "agent_strong": {
        "description": "Agentic benchmark evidence",
        "test": lambda v, o: v.get("agentic_score") and v["agentic_score"] >= 70,
    },
}


class ScoringEngine:
    """One canonical scoring engine."""
    
    def __init__(self):
        self.dimensions = {}
        self.evidence = {}
    
    def score_route(self, offer: dict, endpoint: dict = None, 
                    workload: dict = None) -> dict:
        """Score a route (model × endpoint × offer).
        
        Returns:
            {
                "score": float,
                "coverage": float,  # 0-1, how many dimensions measured
                "confidence": float,  # 0-1, overall confidence
                "dimensions": {...},
                "badges": [...],
                "excluded_reasons": [...]
            }
        """
        result = {
            "score": 0,
            "coverage": 0,
            "confidence": 0,
            "dimensions": {},
            "badges": [],
            "excluded_reasons": [],
        }
        
        # Hard gates first
        excluded = self._check_hard_gates(offer, endpoint, workload)
        if excluded:
            result["excluded_reasons"] = excluded
            result["score"] = 0
            return result
        
        # Score dimensions
        dims = {}
        
        # Quality (from benchmarks)
        quality = self._score_quality(offer)
        if quality is not None:
            dims["quality"] = quality
        
        # Economics
        economics = self._score_economics(offer, workload)
        if economics is not None:
            dims["economics"] = economics
        
        # Reliability
        reliability = self._score_reliability(offer)
        if reliability is not None:
            dims["reliability"] = reliability
        
        # Throughput
        throughput = self._score_throughput(offer, endpoint)
        if throughput is not None:
            dims["throughput"] = throughput
        
        # Capacity
        capacity = self._score_capacity(offer)
        if capacity is not None:
            dims["capacity"] = capacity
        
        # Capability
        capability = self._score_capability(offer)
        if capability is not None:
            dims["capability"] = capability
        
        # Geometric mean (bottleneck-aware)
        if dims:
            # Use geometric mean to penalize weaknesses
            values = [max(0.01, v) for v in dims.values()]  # Avoid log(0)
            base = math.exp(sum(math.log(v) for v in values) / len(values))
            
            # Evidence penalty
            coverage = len(dims) / 6  # 6 possible dimensions
            confidence = self._compute_confidence(dims)
            
            result["score"] = round(base * coverage * confidence, 2)
            result["coverage"] = round(coverage, 2)
            result["confidence"] = round(confidence, 2)
            result["dimensions"] = dims
        
        # Derive badges
        result["badges"] = self._derive_badges(result, offer)
        
        return result
    
    def _check_hard_gates(self, offer, endpoint, workload) -> list:
        """Check hard constraints. Returns exclusion reasons."""
        reasons = []
        
        # Price must be known for budget constraint
        if workload and workload.get("max_cost_usd") is not None:
            if offer.get("input_per_m") is None and not offer.get("free"):
                reasons.append("PRICE_UNKNOWN")
        
        # Tool requirement
        if workload and workload.get("requires_tools"):
            tools = offer.get("metadata", {}).get("tool_call")
            if tools is False:
                reasons.append("TOOLS_NOT_SUPPORTED")
            # UNKNOWN tools: exclude by default for hard constraint
        
        # Context requirement
        if workload and workload.get("min_context"):
            ctx = offer.get("context_tokens")
            if ctx is None:
                reasons.append("CONTEXT_UNKNOWN")
            elif ctx < workload["min_context"]:
                reasons.append("CONTEXT_INSUFFICIENT")
        
        return reasons
    
    def _score_quality(self, offer) -> Optional[float]:
        """Score quality from benchmarks."""
        meta = offer.get("metadata", {})
        benchmarks = meta.get("benchmarks", [])
        
        if not benchmarks:
            return None
        
        # Get domain-specific scores
        coding_scores = []
        agentic_scores = []
        
        for b in benchmarks:
            if not isinstance(b, dict):
                continue
            name = b.get("name", "")
            score = b.get("score")
            if score is None:
                continue
            
            if any(cb in name for cb in ["SWE-Bench", "Aider", "LiveCodeBench"]):
                coding_scores.append(score)
            if any(ab in name for ab in ["OSWorld", "Toolathlon", "AgentBench"]):
                agentic_scores.append(score)
        
        # Use best available
        if coding_scores:
            return sum(coding_scores) / len(coding_scores)
        elif agentic_scores:
            return sum(agentic_scores) / len(agentic_scores)
        elif benchmarks:
            # Last resort: median of all
            all_scores = [b.get("score", 0) for b in benchmarks if isinstance(b, dict)]
            if all_scores:
                all_scores.sort()
                return all_scores[len(all_scores) // 2]
        
        return None
    
    def _score_economics(self, offer, workload) -> Optional[float]:
        """Score economics (lower cost = higher score)."""
        if offer.get("free"):
            return 100
        
        in_m = offer.get("input_per_m")
        if in_m is None:
            return None
        
        # Use workload-specific cost if available
        if workload:
            # Estimate cost for this workload
            input_tokens = workload.get("input_tokens", 1000)
            output_tokens = workload.get("output_tokens", 500)
            requests = workload.get("requests", 1)
            
            cost = (in_m * input_tokens + (offer.get("output_per_m") or 0) * output_tokens) / 1_000_000 * requests
            # Normalize: $0 = 100, $0.01 = 90, $0.10 = 70, $1 = 40, $10 = 10
            return max(0, min(100, 100 - (cost * 10)))
        else:
            # Generic normalization
            return max(0, min(100, 100 - (in_m * 10)))
    
    def _score_reliability(self, offer) -> Optional[float]:
        """Score reliability from actual health data."""
        meta = offer.get("metadata", {})
        reliability = meta.get("reliability")
        
        if reliability is not None:
            return reliability
        
        # Check source health
        source_url = offer.get("source_url", "")
        if "openrouter" in source_url:
            return 90  # OpenRouter is generally reliable
        elif "opencode" in source_url:
            return 85
        
        return None  # Unknown, don't fake it
    
    def _score_throughput(self, offer, endpoint) -> Optional[float]:
        """Score throughput from endpoint measurements."""
        if endpoint:
            tps = endpoint.get("throughput_p50_tps")
            if tps is not None:
                return min(100, tps / 2)  # 50 TPS = 25, 200 TPS = 100
        
        # Check metadata
        meta = offer.get("metadata", {})
        tps = meta.get("throughput_tps")
        if tps:
            return min(100, tps / 2)
        
        return None
    
    def _score_capacity(self, offer) -> Optional[float]:
        """Score capacity (quota)."""
        rph = offer.get("requests_per_5h")
        rpd = offer.get("requests_per_day")
        
        if rph:
            return min(100, rph / 100)  # 100 req/5h = 10, 1000 = 100
        elif rpd:
            return min(100, rpd / 1000)  # 1000 req/day = 10, 10000 = 100
        
        return None
    
    def _score_capability(self, offer) -> Optional[float]:
        """Score capability (tools, context, etc.)."""
        meta = offer.get("metadata", {})
        
        score = 50  # baseline
        
        # Tool support
        tools = meta.get("tool_call")
        if tools is True:
            score += 20
        elif tools is False:
            score -= 20
        
        # Context
        ctx = offer.get("context_tokens")
        if ctx and ctx >= 128000:
            score += 15
        elif ctx and ctx >= 32000:
            score += 10
        
        # Free tier
        if offer.get("free"):
            score += 15
        
        return min(100, max(0, score))
    
    def _compute_confidence(self, dims: dict) -> float:
        """Compute confidence based on evidence coverage."""
        total = 6  # possible dimensions
        measured = sum(1 for v in dims.values() if v is not None)
        return measured / total
    
    def _derive_badges(self, result: dict, offer: dict) -> list:
        """Derive badges from scoring result."""
        badges = []
        dims = result.get("dimensions", {})
        
        for badge_id, badge_def in BADGES.items():
            if badge_def["test"](dims, offer):
                badges.append(badge_id)
        
        return badges
