"""app/mega_deals.py — Detect abnormal/institutional-quality deals.

A mega deal is any offer where:
- Capacity is significantly above baseline (>3x)
- Free with unusual quota (>10K requests)
- Multiplier deal (2x+ usage)
- Price anomaly (significantly below market)
"""
from __future__ import annotations

import json
from typing import Any


def detect_mega_deals(offers: list[dict]) -> list[dict]:
    """Scan all offers and flag mega deals."""
    mega = []

    # Group by source to establish baselines
    by_source = {}
    for o in offers:
        src = o.get("provider_id", "unknown")
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(o)

    for o in offers:
        reasons = []
        score = 0

        # 1. Capacity multiplier (MiMo pattern)
        cap_mult = o.get("metadata", {}).get("capacity_ratio_vs_median") or o.get("metadata", {}).get("capacity_multiplier")
        if cap_mult and cap_mult >= 3.0:
            reasons.append("%s capacity vs baseline" % ("%.1fx" % cap_mult))
            score += min(40, cap_mult * 5)

        # 2. Explicit usage multiplier (Luna pattern)
        usage_mult = o.get("metadata", {}).get("multiplier") or o.get("usage_multiplier")
        if usage_mult and usage_mult >= 2.0:
            reasons.append("%sx usage multiplier" % usage_mult)
            score += min(30, usage_mult * 10)

        # 3. High free quota (>10K requests)
        rph = o.get("metadata", {}).get("requests_per_5h") or o.get("requests_per_5h") or o.get("requests_day")
        if o.get("free") and rph and rph >= 10000:
            reasons.append("Free with %s requests" % f"{rph:,}")
            score += min(30, rph / 500)
        
        # 3b. Very high quota (>10K requests) even if not free
        if rph and rph >= 10000:
            reasons.append("Very high quota: %s req/5h" % f"{rph:,}")
            score += min(30, rph / 1000)

        # 4. Free with very high capacity
        if o.get("free") and cap_mult and cap_mult >= 5.0:
            reasons.append("Free + %.1fx capacity" % cap_mult)
            score += 20

        # 5. Price anomaly (if we have market data)
        in_m = o.get("input_per_m")
        if in_m is not None and in_m == 0 and not o.get("free"):
            # $0 price but not marked free — unusual
            reasons.append("$0 price (not marked free)")
            score += 15

        # 6. Free with extreme context (>1M tokens) — genuine mega deal
        ctx = o.get("context_tokens") or 0
        if o.get("free") and ctx >= 1000000:
            reasons.append("Free with %sK context" % f"{ctx//1000:,}")
            score += min(40, ctx / 100000)

        # 7. Free with high context (>500K tokens)
        if o.get("free") and ctx >= 500000 and ctx < 1000000:
            reasons.append("Free with %sK context" % f"{ctx//1000:,}")
            score += min(20, ctx / 100000)

        # 8. Multi-provider arbitrage (same model, dramatically different price)
        # This would need cross-provider comparison — skip for now

        if reasons and score >= 20:
            mega.append({
                **o,
                "mega_score": min(100, score),
                "mega_reasons": reasons,
                "mega_category": _categorize_mega(reasons),
            })

    mega.sort(key=lambda x: x["mega_score"], reverse=True)
    return mega


def _categorize_mega(reasons: list[str]) -> str:
    """Categorize the mega deal type."""
    text = " ".join(reasons).lower()
    if "capacity" in text and "free" in text:
        return "free_capacity"
    elif "capacity" in text:
        return "capacity_anomaly"
    elif "multiplier" in text:
        return "usage_multiplier"
    elif "free" in text:
        return "high_quota_free"
    else:
        return "price_anomaly"


def get_mega_deal_summary(offers: list[dict]) -> dict:
    """Get a summary of mega deals across all providers."""
    mega = detect_mega_deals(offers)

    by_category = {}
    for m in mega:
        cat = m.get("mega_category", "unknown")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "model": m.get("model_id"),
            "provider": m.get("provider_id"),
            "score": m.get("mega_score"),
            "reasons": m.get("mega_reasons"),
        })

    return {
        "total_mega_deals": len(mega),
        "by_category": by_category,
        "top_deals": [{
            "model": m.get("model_id"),
            "provider": m.get("provider_id"),
            "score": m.get("mega_score"),
            "category": m.get("mega_category"),
            "reasons": m.get("mega_reasons"),
        } for m in mega[:10]],
    }
