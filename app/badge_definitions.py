"""Badge Definitions — Semantic tests for each badge.

Each badge has:
- description: what it means
- test: function that returns True if badge applies
- requirements: what evidence is needed
"""
from __future__ import annotations


BADGES = {
    # Factual tags (no judgment)
    "free": {
        "description": "Zero-price or allowance mechanism explicitly known",
        "category": "factual",
        "test": lambda v, o: o.get("free") is True,
        "evidence_required": "free flag from provider",
    },
    "promo": {
        "description": "Temporary economic improvement",
        "category": "factual",
        "test": lambda v, o: (o.get("usage_multiplier") or 0) > 1,
        "evidence_required": "usage_multiplier > 1",
    },
    "tool_capable": {
        "description": "Supports tools (measured or asserted)",
        "category": "factual",
        "test": lambda v, o: v.get("tools_supported") in ["measured", "asserted"],
        "evidence_required": "tool_call metadata or measurement",
    },
    "vision_capable": {
        "description": "Supports image input",
        "category": "factual",
        "test": lambda v, o: "image" in str(o.get("metadata", {}).get("input_modalities", [])),
        "evidence_required": "input_modalities metadata",
    },
    "json_capable": {
        "description": "Supports structured output",
        "category": "factual",
        "test": lambda v, o: v.get("json_support") is True,
        "evidence_required": "response_format support",
    },
    "long_context": {
        "description": "Large advertised context (≥128K)",
        "category": "factual",
        "test": lambda v, o: (o.get("context_tokens") or 0) >= 128000,
        "evidence_required": "context_tokens from provider",
    },
    "openai_compatible": {
        "description": "Uses OpenAI-compatible API",
        "category": "factual",
        "test": lambda v, o: o.get("metadata", {}).get("openai_compatible", False),
        "evidence_required": "provider documentation",
    },
    
    # Measured tags (empirical)
    "low_latency": {
        "description": "Low measured TTFT (≤200ms)",
        "category": "measured",
        "test": lambda v, o: v.get("ttft_ms") is not None and v["ttft_ms"] <= 200,
        "evidence_required": "TTFT measurement from probe",
    },
    "high_throughput": {
        "description": "High measured TPS (≥50)",
        "category": "measured",
        "test": lambda v, o: v.get("throughput_tps") is not None and v["throughput_tps"] >= 50,
        "evidence_required": "TPS measurement from probe",
    },
    "reliable_endpoint": {
        "description": "High measured availability (≥99%)",
        "category": "measured",
        "test": lambda v, o: v.get("availability") is not None and v["availability"] >= 0.99,
        "evidence_required": "availability measurement from probe",
    },
    "tool_proven": {
        "description": "Measured tool success (≥80%)",
        "category": "measured",
        "test": lambda v, o: v.get("tools_success_rate") is not None and v["tools_success_rate"] >= 0.8,
        "evidence_required": "tool success rate from probe",
    },
    "long_context_proven": {
        "description": "Measured long-context performance",
        "category": "measured",
        "test": lambda v, o: v.get("long_context_score") is not None and v["long_context_score"] >= 70,
        "evidence_required": "long-context benchmark",
    },
    
    # Quality tags (benchmark-based)
    "coding_strong": {
        "description": "Strong coding benchmark evidence (≥70)",
        "category": "quality",
        "test": lambda v, o: v.get("coding_score") is not None and v["coding_score"] >= 70,
        "evidence_required": "coding benchmark (SWE-Bench, Aider, etc.)",
    },
    "reasoning_strong": {
        "description": "Strong reasoning benchmark evidence (≥70)",
        "category": "quality",
        "test": lambda v, o: v.get("reasoning_score") is not None and v["reasoning_score"] >= 70,
        "evidence_required": "reasoning benchmark (GPQA, MMLU-Pro, etc.)",
    },
    "agent_strong": {
        "description": "Strong agentic benchmark evidence (≥70)",
        "category": "quality",
        "test": lambda v, o: v.get("agentic_score") is not None and v["agentic_score"] >= 70,
        "evidence_required": "agentic benchmark (OSWorld, Toolathlon, etc.)",
    },
    "frontier_coding": {
        "description": "Current relative frontier for coding",
        "category": "quality",
        "test": lambda v, o: v.get("coding_percentile") is not None and v["coding_percentile"] >= 90,
        "evidence_required": "coding benchmark + cohort comparison",
    },
    "frontier_reasoning": {
        "description": "Current relative frontier for reasoning",
        "category": "quality",
        "test": lambda v, o: v.get("reasoning_percentile") is not None and v["reasoning_percentile"] >= 90,
        "evidence_required": "reasoning benchmark + cohort comparison",
    },
    
    # Decision labels (workload-dependent)
    "workhorse": {
        "description": "Broad sustained workload fitness",
        "category": "decision",
        "test": lambda v, o: v.get("workhorse_score") is not None and v["workhorse_score"] >= 70,
        "evidence_required": "workhorse score with coverage ≥ 0.7",
    },
    "high_value": {
        "description": "Good quality/cost frontier for stated workload",
        "category": "decision",
        "test": lambda v, o: v.get("value_score") is not None and v["value_score"] >= 80,
        "evidence_required": "value score with quality + cost data",
    },
}


def get_badge_info(badge_id: str) -> dict:
    """Get badge definition."""
    return BADGES.get(badge_id, {})


def list_badges(category: str = None) -> list[dict]:
    """List all badges, optionally filtered by category."""
    result = []
    for badge_id, badge_def in BADGES.items():
        if category and badge_def.get("category") != category:
            continue
        result.append({"id": badge_id, **badge_def})
    return result
