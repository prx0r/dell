"""app/categories.py — Custom categorizations for the deal aggregator.

The CoinGecko-style categories that devs actually care about:
- Best Workhorse (agentic, batch, large tasks)
- Best Price-to-Intelligence Ratio
- Easiest to Get (setup difficulty)
- Best Free Tier (actual daily capacity)
- Fastest Inference
- Best for Long Context
- Best for Vision
- Best for Tool Calling (agents)
- Provider Health + Reliability
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_offers() -> list[dict]:
    """Load all offers from snapshots."""
    snapshots_dir = ROOT / "snapshots"
    offers = []
    if snapshots_dir.exists():
        for f in snapshots_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                offers.extend(data.get("offers", []))
            except Exception:
                continue
    return offers


def _load_providers() -> dict:
    """Load provider metadata."""
    from providers import PROVIDERS, to_dict
    return {pid: to_dict(p) for pid, p in PROVIDERS.items()}


def best_workhorses(limit: int = 15) -> dict:
    """Best models for agentic/batch/large tasks.

    Criteria: low cost per token + high context + tool calling + high daily capacity.
    The model that can do ALL the work without running out of quota.
    """
    offers = _load_offers()
    providers = _load_providers()

    scored = []
    for o in offers:
        pid = o.get("provider_id", "")
        prov = providers.get(pid, {})

        # Skip community leads
        if o.get("offer_kind") == "community_lead":
            continue

        in_m = o.get("input_per_m") or 0
        out_m = o.get("output_per_m") or 0

        # Cost score (lower = better, 0 means free = max)
        if in_m == 0 and out_m == 0:
            cost_score = 100
        elif in_m > 0:
            # Normalize: $0.1/M = 80, $1/M = 50, $10/M = 20
            cost_score = max(0, 100 - (in_m * 10))
        else:
            cost_score = 50

        # Context score
        ctx = o.get("context_tokens") or prov.get("context_window_max") or 0
        ctx_score = min(100, ctx / 1000)  # 100K = 100

        # Capability score
        cap_score = 0
        if prov.get("has_tool_calling"): cap_score += 30
        if prov.get("has_structured_output"): cap_score += 20
        if prov.get("has_batch_api"): cap_score += 20
        if prov.get("has_reasoning"): cap_score += 15
        if o.get("free"): cap_score += 15

        # Capacity score (requests/day)
        rpd = o.get("requests_day") or prov.get("free_requests_day") or 100
        cap_daily = min(100, rpd / 10)

        # Workhorse score = weighted combination
        score = (cost_score * 0.35 +
                 ctx_score * 0.2 +
                 cap_score * 0.25 +
                 cap_daily * 0.2)

        scored.append({
            **o,
            "workhorse_score": round(score, 1),
            "cost_score": round(cost_score, 1),
            "context_score": round(ctx_score, 1),
            "capability_score": round(cap_score, 1),
            "capacity_score": round(cap_daily, 1),
            "category": "best_workhorse",
            "why": _workhorse_why(cost_score, ctx_score, cap_score, cap_daily, o, prov),
        })

    scored.sort(key=lambda x: x["workhorse_score"], reverse=True)
    return {
        "category": "best_workhorse",
        "description": "Best for agentic batch tasks — low cost, high context, tool calling, high daily capacity",
        "criteria": "35% cost + 25% capabilities + 20% context + 20% daily capacity",
        "picks": scored[:limit],
    }


def best_value_ratios(limit: int = 15) -> dict:
    """Best price-to-intelligence ratio.

    For each model, estimate intelligence from available benchmarks/features,
    then compute: intelligence / cost.
    """
    offers = _load_offers()
    providers = _load_providers()

    scored = []
    for o in offers:
        if o.get("offer_kind") == "community_lead":
            continue
        in_m = o.get("input_per_m") or 0
        if in_m <= 0:
            continue  # free or bad data — skip for value ratio

        pid = o.get("provider_id", "")
        prov = providers.get(pid, {})

        # Intelligence estimate from AA index or capabilities
        meta = o.get("metadata", {})
        intel = meta.get("intelligence_index") or meta.get("agentic_index") or 50
        if not meta.get("intelligence_index"):
            # Fallback: estimate from capabilities
            if prov.get("has_reasoning"): intel += 15
            if prov.get("has_tool_calling"): intel += 10
            if prov.get("has_vision"): intel += 5
            if prov.get("has_structured_output"): intel += 5
            ctx = o.get("context_tokens") or 0
            if ctx > 100000: intel += 10
            if ctx > 200000: intel += 5

        # Value ratio = intelligence / cost_per_1m_tokens
        ratio = intel / max(in_m, 0.01)

        scored.append({
            **o,
            "value_ratio": round(ratio, 1),
            "intelligence_estimate": intel,
            "category": "best_value_ratio",
        })

    scored.sort(key=lambda x: x["value_ratio"], reverse=True)
    return {
        "category": "best_value_ratio",
        "description": "Best intelligence per dollar — which model gives you the most brain for your buck",
        "picks": scored[:limit],
    }


def easiest_to_get(limit: int = 15) -> dict:
    """Easiest deals to claim — sorted by setup difficulty.

    1 = instant (API key only)
    2 = account + key
    3 = approval process
    4 = enterprise contract
    """
    from providers import PROVIDERS, to_dict

    providers = sorted(PROVIDERS.values(), key=lambda p: p.setup_difficulty)

    return {
        "category": "easiest_to_get",
        "description": "Sorted by setup difficulty — from instant API key to enterprise contract",
        "difficulty_scale": {
            "1": "Instant — API key only, no approval",
            "2": "Account required — sign up + verify",
            "3": "Approval needed — wait for access",
            "4": "Enterprise — contract required",
        },
        "picks": [to_dict(p) for p in providers[:limit]],
    }


def best_free_tiers(limit: int = 15) -> dict:
    """Best free tiers ranked by actual daily capacity.

    Not just "free" — but how much can you actually USE per day?
    """
    offers = _load_offers()
    providers = _load_providers()

    free = []
    for o in offers:
        if not o.get("free"):
            continue
        pid = o.get("provider_id", "")
        prov = providers.get(pid, {})

        rpd = o.get("requests_day") or prov.get("free_requests_day") or 0
        tpd = o.get("tokens_day") or prov.get("free_tokens_day") or 0
        rpm = o.get("requests_minute") or prov.get("free_requests_minute") or 0

        # Capacity score: how much can you actually use daily
        capacity = rpd * 1000 + tpd  # rough composite
        if capacity == 0:
            capacity = 500  # unknown = some capacity

        ctx = o.get("context_tokens") or prov.get("context_window_max") or 0

        scored = {
            **o,
            "daily_capacity": capacity,
            "requests_per_day": rpd,
            "tokens_per_day": tpd,
            "requests_per_minute": rpm,
            "context_window": ctx,
            "setup_difficulty": prov.get("setup_difficulty", 3),
            "agentic_notes": prov.get("agentic_notes", ""),
            "category": "best_free_tier",
        }
        free.append(scored)

    free.sort(key=lambda x: (-x["daily_capacity"], x["setup_difficulty"]))
    return {
        "category": "best_free_tier",
        "description": "Free models ranked by actual daily capacity — how much can you really use?",
        "note": "Capacity is estimated from rate limits. Some providers don't publish exact limits.",
        "picks": free[:limit],
    }


def fastest_inference(limit: int = 15) -> dict:
    """Fastest inference — sorted by latency."""
    offers = _load_offers()
    providers = _load_providers()

    scored = []
    for o in offers:
        pid = o.get("provider_id", "")
        prov = providers.get(pid, {})
        latency = prov.get("avg_latency_ms")
        if latency is None:
            continue
        scored.append({
            **o,
            "latency_ms": latency,
            "category": "fastest_inference",
        })

    scored.sort(key=lambda x: x["latency_ms"])
    return {
        "category": "fastest_inference",
        "description": "Fastest inference providers — for real-time agents and interactive use",
        "picks": scored[:limit],
    }


def best_for_vision(limit: int = 10) -> dict:
    """Best models that accept image input."""
    offers = _load_offers()
    providers = _load_providers()

    vision = []
    for o in offers:
        pid = o.get("provider_id", "")
        prov = providers.get(pid, {})
        if not prov.get("has_vision"):
            continue
        in_m = o.get("input_per_m") or 0
        vision.append({**o, "category": "best_for_vision", "cost_per_1m": in_m})

    vision.sort(key=lambda x: x["cost_per_1m"])
    return {
        "category": "best_for_vision",
        "description": "Models that accept image input, sorted by cost",
        "picks": vision[:limit],
    }


def best_for_agents(limit: int = 10) -> dict:
    """Best models for autonomous agents — tool calling + structured output + reliability."""
    offers = _load_offers()
    providers = _load_providers()

    scored = []
    for o in offers:
        pid = o.get("provider_id", "")
        prov = providers.get(pid, {})

        score = 0
        if prov.get("has_tool_calling"): score += 30
        if prov.get("has_structured_output"): score += 25
        if prov.get("has_reasoning"): score += 15
        if prov.get("has_batch_api"): score += 10
        if o.get("free"): score += 10
        in_m = o.get("input_per_m") or 0
        if in_m < 1: score += 10
        if in_m == 0: score += 5

        if score < 30:
            continue

        scored.append({
            **o,
            "agent_score": score,
            "category": "best_for_agents",
            "why": f"Tool calling={'yes' if prov.get('has_tool_calling') else 'no'}, "
                   f"Structured output={'yes' if prov.get('has_structured_output') else 'no'}, "
                   f"Cost=${in_m:.2f}/M",
        })

    scored.sort(key=lambda x: x["agent_score"], reverse=True)
    return {
        "category": "best_for_agents",
        "description": "Best for autonomous agents — tool calling, structured output, reliability, cost",
        "picks": scored[:limit],
    }


def provider_comparison(limit: int = 20) -> dict:
    """Side-by-side provider comparison — the full aggregator view."""
    from providers import PROVIDERS, to_dict

    providers = []
    for p in PROVIDERS.values():
        d = to_dict(p)
        # Count offers per provider
        offers = _load_offers()
        provider_offers = [o for o in offers if o.get("provider_id") == p.provider_id]
        free_count = sum(1 for o in provider_offers if o.get("free"))
        d["total_offers"] = len(provider_offers)
        d["free_offers"] = free_count
        providers.append(d)

    providers.sort(key=lambda x: x["setup_difficulty"])
    return {
        "category": "provider_comparison",
        "description": "Full provider comparison — setup difficulty, free tier, features, pricing",
        "picks": providers[:limit],
    }


def _workhorse_why(cost, ctx, cap, daily, offer, prov):
    parts = []
    if offer.get("free"):
        parts.append("FREE")
    elif cost > 80:
        parts.append("very cheap")
    elif cost > 50:
        parts.append("affordable")
    if ctx > 80:
        parts.append(f"large context ({offer.get('context_tokens', prov.get('context_window_max', '?'))} tokens)")
    if prov.get("has_tool_calling"):
        parts.append("tool calling")
    if prov.get("has_batch_api"):
        parts.append("batch API")
    if daily > 80:
        parts.append("high daily capacity")
    return " + ".join(parts) if parts else "solid all-rounder"


# Registry of all categories
ALL_CATEGORIES = {
    "workhorse": best_workhorses,
    "value": best_value_ratios,
    "easy": easiest_to_get,
    "free": best_free_tiers,
    "fast": fastest_inference,
    "vision": best_for_vision,
    "agents": best_for_agents,
    "providers": provider_comparison,
}


def get_category(name: str, limit: int = 15) -> dict:
    fn = ALL_CATEGORIES.get(name)
    if not fn:
        return {"error": f"Unknown category: {name}", "available": list(ALL_CATEGORIES.keys())}
    return fn(limit)


def list_categories() -> list[dict]:
    return [
        {"id": "workhorse", "name": "Best Workhorse", "description": "Best for agentic batch tasks"},
        {"id": "value", "name": "Best Value Ratio", "description": "Intelligence per dollar"},
        {"id": "easy", "name": "Easiest to Get", "description": "Sorted by setup difficulty"},
        {"id": "free", "name": "Best Free Tier", "description": "Ranked by daily capacity"},
        {"id": "fast", "name": "Fastest Inference", "description": "Lowest latency"},
        {"id": "vision", "name": "Best for Vision", "description": "Image-capable models"},
        {"id": "agents", "name": "Best for Agents", "description": "Tool calling + structured output"},
        {"id": "providers", "name": "Provider Comparison", "description": "Full side-by-side"},
    ]
