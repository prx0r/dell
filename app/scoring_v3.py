"""Scoring V3 — Final semantic scoring.

Key fixes:
- Confidence != coverage
- No neutral 50 for unknown
- Context is NOT quality
- Task-specific weighting
"""
from __future__ import annotations

import json
import math
from typing import Optional


# Task profiles for domain-specific scoring
TASK_PROFILES = {
    "coding": {
        "quality_weight": 0.40,
        "cost_weight": 0.30,
        "reliability_weight": 0.20,
        "throughput_weight": 0.10,
        "required_capabilities": ["tools"],
        "benchmark_domains": ["coding"],
    },
    "research": {
        "quality_weight": 0.35,
        "cost_weight": 0.25,
        "reliability_weight": 0.20,
        "throughput_weight": 0.20,
        "required_capabilities": ["long_context"],
        "benchmark_domains": ["reasoning"],
    },
    "agentic": {
        "quality_weight": 0.30,
        "cost_weight": 0.25,
        "reliability_weight": 0.25,
        "throughput_weight": 0.20,
        "required_capabilities": ["tools", "json_schema"],
        "benchmark_domains": ["agentic"],
    },
    "general": {
        "quality_weight": 0.25,
        "cost_weight": 0.35,
        "reliability_weight": 0.25,
        "throughput_weight": 0.15,
        "required_capabilities": [],
        "benchmark_domains": ["general"],
    },
}


class ScoringV3:
    """Final scoring engine with semantic correctness."""
    
    def __init__(self):
        self.task_profiles = TASK_PROFILES
    
    def score_route(self, route: dict, task: str = "general") -> dict:
        """Score a route for a specific task."""
        profile = self.task_profiles.get(task, self.task_profiles["general"])
        
        result = {
            "score": 0,
            "coverage": 0,
            "confidence": 0,
            "dimensions": {},
            "badges": [],
            "excluded_reasons": [],
        }
        
        # Check eligibility
        excluded = self._check_eligibility(route, profile)
        if excluded:
            result["excluded_reasons"] = excluded
            return result
        
        # Score dimensions
        dims = {}
        
        # Quality (from benchmarks ONLY, not context)
        quality = self._score_quality(route, profile)
        if quality is not None:
            dims["quality"] = quality
        
        # Economics
        economics = self._score_economics(route)
        if economics is not None:
            dims["economics"] = economics
        
        # Reliability
        reliability = self._score_reliability(route)
        if reliability is not None:
            dims["reliability"] = reliability
        
        # Throughput
        throughput = self._score_throughput(route)
        if throughput is not None:
            dims["throughput"] = throughput
        
        # Capacity
        capacity = self._score_capacity(route)
        if capacity is not None:
            dims["capacity"] = capacity
        
        # Capability (factual, not weighted)
        capability = self._score_capability(route)
        if capability is not None:
            dims["capability"] = capability
        
        # Task-weighted scoring (not geometric mean of present dimensions)
        if dims:
            score = 0
            for dim_name, dim_value in dims.items():
                weight = self._get_dimension_weight(dim_name, profile)
                score += weight * dim_value
            
            # Coverage: fraction of required dimensions present
            required_dims = ["quality", "economics", "reliability", "throughput"]
            coverage = sum(1 for d in required_dims if d in dims) / len(required_dims)
            
            # Confidence: based on evidence quality, NOT coverage
            confidence = self._compute_confidence(dims, route)
            
            result["score"] = round(score, 2)
            result["coverage"] = round(coverage, 2)
            result["confidence"] = round(confidence, 2)
            result["dimensions"] = dims
        
        # Derive badges
        result["badges"] = self._derive_badges(result, route, task)
        
        return result
    
    def _check_eligibility(self, route: dict, profile: dict) -> list:
        """Check eligibility before scoring."""
        reasons = []
        
        for cap in profile.get("required_capabilities", []):
            if cap == "tools" and route.get("tools_supported") is False:
                reasons.append("TOOLS_NOT_SUPPORTED")
            elif cap == "long_context" and (route.get("context_tokens") or 0) < 128000:
                reasons.append("CONTEXT_INSUFFICIENT")
        
        return reasons
    
    def _get_dimension_weight(self, dim_name: str, profile: dict) -> float:
        """Get weight for a dimension from task profile."""
        weight_map = {
            "quality": profile.get("quality_weight", 0.25),
            "economics": profile.get("cost_weight", 0.35),
            "reliability": profile.get("reliability_weight", 0.25),
            "throughput": profile.get("throughput_weight", 0.15),
            "capacity": 0.10,
            "capability": 0.10,
        }
        return weight_map.get(dim_name, 0.10)
    
    def _score_quality(self, route: dict, profile: dict) -> Optional[float]:
        """Score quality from benchmarks ONLY."""
        meta = route.get("metadata", {})
        benchmarks = meta.get("benchmarks", [])
        
        if not benchmarks:
            return None  # Unknown — do NOT use context as proxy
        
        domain = profile.get("benchmark_domains", ["general"])[0]
        scores = []
        
        for b in benchmarks:
            if not isinstance(b, dict):
                continue
            name = b.get("name", "")
            score = b.get("score")
            if score is None:
                continue
            
            if domain == "coding" and any(cb in name for cb in ["SWE-Bench", "Aider", "LiveCodeBench"]):
                scores.append(score)
            elif domain == "reasoning" and any(rb in name for rb in ["GPQA", "MMLU-Pro", "FrontierMath"]):
                scores.append(score)
            elif domain == "agentic" and any(ab in name for ab in ["OSWorld", "Toolathlon", "AgentBench"]):
                scores.append(score)
            elif domain == "general":
                scores.append(score)
        
        if scores:
            return sum(scores) / len(scores)
        
        return None
    
    def _score_economics(self, route: dict) -> Optional[float]:
        """Score economics (lower cost = higher score)."""
        if route.get("free"):
            return 100
        
        in_m = route.get("input_per_m")
        if in_m is None:
            return None  # Unknown — do NOT coerce
        
        return max(0, min(100, 100 - (in_m * 10)))
    
    def _score_reliability(self, route: dict) -> Optional[float]:
        """Score reliability from endpoint observations."""
        reliability = route.get("reliability")
        if reliability is not None:
            return reliability
        
        return None  # Unknown — do NOT use neutral 50
    
    def _score_throughput(self, route: dict) -> Optional[float]:
        """Score throughput from endpoint measurements."""
        tps = route.get("throughput_tps")
        if tps is not None:
            return min(100, tps / 2)
        
        return None  # Unknown — do NOT use neutral 50
    
    def _score_capacity(self, route: dict) -> Optional[float]:
        """Score capacity (quota)."""
        rph = route.get("requests_per_5h")
        rpd = route.get("requests_per_day")
        
        if rph:
            return min(100, rph / 100)
        elif rpd:
            return min(100, rpd / 1000)
        
        return None
    
    def _score_capability(self, route: dict) -> Optional[float]:
        """Score capability (factual, not weighted)."""
        meta = route.get("metadata", {})
        
        tools = meta.get("tool_call")
        if tools is True:
            return 80
        elif tools is False:
            return 20
        else:
            return None  # Unknown
    
    def _compute_confidence(self, dims: dict, route: dict) -> float:
        """Compute confidence based on evidence QUALITY, not quantity.
        
        Confidence is about:
        - Source authority
        - Measurement recency
        - Corroboration
        - NOT just number of dimensions present
        """
        confidence_factors = []
        
        # Source authority (from reliability)
        if route.get("reliability") is not None:
            confidence_factors.append(route["reliability"] / 100)
        
        # Measurement recency (assume recent if measured)
        if route.get("throughput_tps") is not None:
            confidence_factors.append(0.9)
        
        # Corroboration (if multiple dimensions have data)
        if len(dims) > 3:
            confidence_factors.append(0.8)
        
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.3  # Low confidence when no evidence
    
    def _derive_badges(self, result: dict, route: dict, task: str) -> list:
        """Derive badges from scoring result."""
        badges = []
        dims = result.get("dimensions", {})
        
        if route.get("free"):
            badges.append("free")
        
        if result["score"] >= 70 and result["coverage"] >= 0.7:
            badges.append("workhorse")
        
        if result["score"] >= 80:
            badges.append("high_value")
        
        meta = route.get("metadata", {})
        if meta.get("tool_call") is True:
            badges.append("tool_capable")
        
        if route.get("context_tokens", 0) >= 128000:
            badges.append("long_context")
        
        return badges
