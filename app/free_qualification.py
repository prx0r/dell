"""app/free_qualification.py — Qualify free deals by actual utility.

Not all free deals are equal. This system scores free offers by:
- Context window (bigger = more useful)
- Capabilities (tool calling, reasoning, vision)
- Rate limits (if known)
- Provider quality (known reliable vs unknown)
- Deal type (always-free vs promotional vs trial)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def qualify_free_deal(offer: dict) -> dict:
    """Score a free deal by actual utility."""
    meta = offer.get("metadata", {})
    ctx = offer.get("context_tokens") or 0
    rpd = offer.get("requests_per_day") or meta.get("requests_per_5h")
    provider = offer.get("provider_id", "")

    # Context score (0-30)
    if ctx >= 1000000:
        ctx_score = 30
    elif ctx >= 200000:
        ctx_score = 25
    elif ctx >= 128000:
        ctx_score = 20
    elif ctx >= 32000:
        ctx_score = 10
    else:
        ctx_score = 0

    # Capability score (0-25)
    cap_score = 0
    if meta.get("tool_calling"): cap_score += 8
    if meta.get("reasoning"): cap_score += 7
    if meta.get("structured_output"): cap_score += 5
    if meta.get("vision"): cap_score += 5

    # Rate limit score (0-25) — higher if we KNOW the limits
    rate_score = 0
    if rpd:
        if rpd >= 10000: rate_score = 25
        elif rpd >= 1000: rate_score = 20
        elif rpd >= 100: rate_score = 15
        else: rate_score = 10
    else:
        rate_score = 5  # unknown = low confidence

    # Provider quality score (0-20)
    prov_score = 0
    known_good = ["openrouter", "google", "openai", "anthropic", "deepseek",
                  "meta", "mistral", "nvidia", "cohere", "xai", "zhipuai",
                  "moonshotai", "alibaba", "bytedance-seed"]
    if provider in known_good:
        prov_score = 15
    elif provider in ["opencode-go", "opencode-zen", "sensenova", "scaleway"]:
        prov_score = 10
    else:
        prov_score = 5

    total = ctx_score + cap_score + rate_score + prov_score

    # Deal type classification
    deal_type = "always_free"  # default
    if rpd and rpd >= 1000:
        deal_type = "high_capacity_free"
    elif meta.get("multiplier") or meta.get("capacity_multiplier"):
        deal_type = "promotional_free"
    elif meta.get("window_hours"):
        deal_type = "windowed_free"

    # Why this deal matters
    why = []
    if ctx >= 1000000: why.append("1M+ context")
    elif ctx >= 200000: why.append("200K+ context")
    if rpd and rpd >= 1000: why.append("%s req/day" % rpd)
    if meta.get("tool_calling"): why.append("tool calling")
    if meta.get("reasoning"): why.append("reasoning")
    if provider in known_good: why.append("reliable provider")
    if meta.get("capacity_multiplier", 0) >= 3: why.append("%.1fx capacity" % meta["capacity_multiplier"])

    return {
        "utility_score": min(100, total),
        "deal_type": deal_type,
        "context_score": ctx_score,
        "capability_score": cap_score,
        "rate_score": rate_score,
        "provider_score": prov_score,
        "why": why,
        "context_tokens": ctx,
        "requests_per_day": rpd,
    }


def rank_free_deals(offers: list[dict]) -> list[dict]:
    """Rank free deals by actual utility."""
    free = [o for o in offers if o.get("free")]
    qualified = []
    for o in free:
        q = qualify_free_deal(o)
        qualified.append({**o, "_free_qual": q})

    qualified.sort(key=lambda x: x["_free_qual"]["utility_score"], reverse=True)
    return qualified
