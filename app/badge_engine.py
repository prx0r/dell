"""Badge Engine — Semantic badges with explicit basis.

Each badge has:
- description: what it means
- category: factual/measured/quality/decision
- test: function that returns True if badge applies
- basis: what evidence supports this badge
"""
from __future__ import annotations

import json
from typing import Optional


# Badge definitions with semantic tests
BADGES = {
    # Factual tags
    "free": {
        "description": "Zero-price or allowance mechanism explicitly known",
        "category": "factual",
        "test": lambda r, o: o.get("free") is True,
        "basis_template": "Free flag from provider: {source}",
    },
    "promo": {
        "description": "Temporary economic improvement",
        "category": "factual",
        "test": lambda r, o: (o.get("usage_multiplier") or 0) > 1,
        "basis_template": "Usage multiplier: {multiplier}x",
    },
    "tool_capable": {
        "description": "Supports tools (measured or asserted)",
        "category": "factual",
        "test": lambda r, o: o.get("metadata", {}).get("tool_call") is True,
        "basis_template": "Tool support asserted by provider",
    },
    "vision_capable": {
        "description": "Supports image input",
        "category": "factual",
        "test": lambda r, o: "image" in str(o.get("metadata", {}).get("input_modalities", [])),
        "basis_template": "Image modality in provider metadata",
    },
    "long_context": {
        "description": "Large advertised context (≥128K)",
        "category": "factual",
        "test": lambda r, o: (o.get("context_tokens") or 0) >= 128000,
        "basis_template": "Context window: {context_tokens} tokens",
    },
    
    # Measured tags
    "low_latency": {
        "description": "Low measured TTFT (≤200ms)",
        "category": "measured",
        "test": lambda r, o: r.get("ttft_ms") is not None and r["ttft_ms"] <= 200,
        "basis_template": "TTFT measurement: {ttft_ms}ms",
    },
    "high_throughput": {
        "description": "High measured TPS (≥50)",
        "category": "measured",
        "test": lambda r, o: r.get("throughput_tps") is not None and r["throughput_tps"] >= 50,
        "basis_template": "Throughput measurement: {throughput_tps} TPS",
    },
    "reliable_endpoint": {
        "description": "High measured availability (≥99%)",
        "category": "measured",
        "test": lambda r, o: r.get("availability") is not None and r["availability"] >= 0.99,
        "basis_template": "Availability measurement: {availability}%",
    },
    "tool_proven": {
        "description": "Measured tool success (≥80%)",
        "category": "measured",
        "test": lambda r, o: r.get("tools_success_rate") is not None and r["tools_success_rate"] >= 0.8,
        "basis_template": "Tool success rate: {tools_success_rate}%",
    },
    
    # Quality tags
    "coding_strong": {
        "description": "Strong coding benchmark evidence (≥70)",
        "category": "quality",
        "test": lambda r, o: r.get("coding_score") is not None and r["coding_score"] >= 70,
        "basis_template": "Coding benchmark: {coding_score}",
    },
    "reasoning_strong": {
        "description": "Strong reasoning benchmark evidence (≥70)",
        "category": "quality",
        "test": lambda r, o: r.get("reasoning_score") is not None and r["reasoning_score"] >= 70,
        "basis_template": "Reasoning benchmark: {reasoning_score}",
    },
    "agent_strong": {
        "description": "Strong agentic benchmark evidence (≥70)",
        "category": "quality",
        "test": lambda r, o: r.get("agentic_score") is not None and r["agentic_score"] >= 70,
        "basis_template": "Agentic benchmark: {agentic_score}",
    },
    
    # Decision labels
    "workhorse": {
        "description": "Broad sustained workload fitness",
        "category": "decision",
        "test": lambda r, o: r.get("score", 0) >= 70 and r.get("coverage", 0) >= 0.7,
        "basis_template": "Score: {score}, Coverage: {coverage}",
    },
    "high_value": {
        "description": "Good quality/cost frontier for stated workload",
        "category": "decision",
        "test": lambda r, o: r.get("score", 0) >= 80,
        "basis_template": "Score: {score}",
    },
}


class BadgeEngine:
    """Badge engine with semantic tests and basis."""
    
    def __init__(self):
        self.badges = BADGES
    
    def derive_badges(self, scoring_result: dict, offer: dict) -> list[dict]:
        """Derive badges with basis."""
        badges = []
        
        for badge_id, badge_def in self.badges.items():
            if badge_def["test"](scoring_result, offer):
                basis = self._compute_basis(badge_id, badge_def, scoring_result, offer)
                badges.append({
                    "badge": badge_id,
                    "description": badge_def["description"],
                    "category": badge_def["category"],
                    "basis": basis,
                })
        
        return badges
    
    def _compute_basis(self, badge_id: str, badge_def: dict, 
                       scoring_result: dict, offer: dict) -> str:
        """Compute the basis/evidence for a badge."""
        template = badge_def.get("basis_template", "")
        
        # Fill in template variables
        try:
            return template.format(
                source=offer.get("source_url", "unknown"),
                multiplier=offer.get("usage_multiplier", 0),
                context_tokens=offer.get("context_tokens", 0),
                ttft_ms=scoring_result.get("ttft_ms", 0),
                throughput_tps=scoring_result.get("throughput_tps", 0),
                availability=scoring_result.get("availability", 0),
                tools_success_rate=scoring_result.get("tools_success_rate", 0),
                coding_score=scoring_result.get("coding_score", 0),
                reasoning_score=scoring_result.get("reasoning_score", 0),
                agentic_score=scoring_result.get("agentic_score", 0),
                score=scoring_result.get("score", 0),
                coverage=scoring_result.get("coverage", 0),
            )
        except:
            return "Evidence available"
