"""Market baseline calculation and deal scoring engine."""

import math
import logging
from typing import Any

logger = logging.getLogger(__name__)

QUALITY_WEIGHTS = {
    "reliability": 0.3,
    "speed": 0.2,
    "context_window": 0.2,
    "rate_limit": 0.15,
    "features": 0.15,
}


def calculate_market_baseline(offers: list[dict]) -> dict:
    """Calculate market baseline statistics from a list of offers.

    Args:
        offers: List of offer dicts. Each should have at minimum
                'price_usd', 'tokens_per_dollar', and quality metrics.

    Returns:
        Dict with baseline statistics:
            median_price, median_tpd, avg_discount, min_price, max_price,
            price_stddev, tpd_stddev, offer_count
    """
    if not offers:
        logger.warning("Empty offers list, returning empty baseline")
        return {
            "median_price": 0,
            "median_tpd": 0,
            "avg_discount": 0,
            "min_price": 0,
            "max_price": 0,
            "price_stddev": 0,
            "tpd_stddev": 0,
            "offer_count": 0,
        }

    prices = [o.get("price_usd", 0) for o in offers if o.get("price_usd") is not None]
    tpds = [o.get("tokens_per_dollar", 0) for o in offers if o.get("tokens_per_dollar") is not None]
    discounts = [o.get("discount_percent", 0) for o in offers if o.get("discount_percent") is not None]

    def _median(vals: list[float]) -> float:
        if not vals:
            return 0
        s = sorted(vals)
        n = len(s)
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2

    def _stddev(vals: list[float]) -> float:
        if len(vals) < 2:
            return 0
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
        return math.sqrt(variance)

    baseline = {
        "median_price": _median(prices),
        "median_tpd": _median(tpds),
        "avg_discount": sum(discounts) / len(discounts) if discounts else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "price_stddev": _stddev(prices),
        "tpd_stddev": _stddev(tpds),
        "offer_count": len(offers),
    }

    logger.info("Calculated market baseline from %d offers", len(offers))
    return baseline


def _quality_score(offer: dict) -> float:
    """Calculate a normalized quality score (0-1) for an offer."""
    score = 0.0
    total_weight = 0.0

    if "reliability" in offer:
        score += offer["reliability"] * QUALITY_WEIGHTS["reliability"]
        total_weight += QUALITY_WEIGHTS["reliability"]
    if "speed_score" in offer:
        score += offer["speed_score"] * QUALITY_WEIGHTS["speed"]
        total_weight += QUALITY_WEIGHTS["speed"]
    if "context_window" in offer:
        ctx = min(offer["context_window"] / 200000, 1.0)
        score += ctx * QUALITY_WEIGHTS["context_window"]
        total_weight += QUALITY_WEIGHTS["context_window"]
    if "rate_limit_rpm" in offer:
        rl = min(offer["rate_limit_rpm"] / 10000, 1.0)
        score += rl * QUALITY_WEIGHTS["rate_limit"]
        total_weight += QUALITY_WEIGHTS["rate_limit"]
    if "feature_score" in offer:
        score += offer["feature_score"] * QUALITY_WEIGHTS["features"]
        total_weight += QUALITY_WEIGHTS["features"]

    if total_weight == 0:
        return 0.5
    return score / total_weight


def _expiry_urgency(offer: dict) -> float:
    """Calculate urgency multiplier based on offer expiry. Returns 0.5-1.5."""
    expiry = offer.get("promo_expiry")
    if not expiry:
        return 1.0

    try:
        from datetime import datetime
        if isinstance(expiry, str):
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
                try:
                    expiry_dt = datetime.strptime(expiry, fmt)
                    break
                except ValueError:
                    continue
            else:
                return 1.0
        elif isinstance(expiry, datetime):
            expiry_dt = expiry
        else:
            return 1.0

        now = datetime.utcnow()
        days_left = (expiry_dt - now).days

        if days_left < 0:
            return 0.5
        if days_left <= 3:
            return 1.5
        if days_left <= 7:
            return 1.3
        if days_left <= 30:
            return 1.1
        return 1.0
    except Exception as exc:
        logger.debug("Failed to calculate expiry urgency: %s", exc)
        return 1.0


def _source_confidence(offer: dict) -> float:
    """Return source confidence multiplier (0.5-1.0)."""
    conf = offer.get("source_confidence", 0.5)
    return max(0.5, min(1.0, conf))


def score_deals(offers: list[dict], market_baseline: dict) -> list[dict]:
    """Calculate deal score (0-100) for each offer.

    Scoring factors:
        - Discount vs market baseline (0-30 pts)
        - Quality adjusted value (0-25 pts)
        - Rate limit value (0-15 pts)
        - Expiry urgency (0-15 pts)
        - Source confidence (0-15 pts)

    Args:
        offers: List of offer dicts.
        market_baseline: Baseline dict from calculate_market_baseline().

    Returns:
        List of dicts with 'offer' and 'deal_score' (0-100) keys.
    """
    if not offers:
        return []

    results = []
    median_price = market_baseline.get("median_price", 0)
    median_tpd = market_baseline.get("median_tpd", 0)

    for offer in offers:
        try:
            score = 0.0

            price = offer.get("price_usd", 0)
            tpd = offer.get("tokens_per_dollar", 0)
            discount = offer.get("discount_percent", 0)

            if median_price > 0 and price > 0:
                price_ratio = median_price / price
                discount_score = min(price_ratio * 15, 30)
            elif discount > 0:
                discount_score = min(discount * 0.6, 30)
            else:
                discount_score = 0

            quality = _quality_score(offer)
            quality_score = quality * 25

            rl_rpm = offer.get("rate_limit_rpm", 0)
            rl_score = min(rl_rpm / 10000, 1.0) * 15

            urgency = _expiry_urgency(offer)
            urgency_score = (urgency - 0.5) * 20
            urgency_score = max(0, min(15, urgency_score))

            confidence = _source_confidence(offer)
            confidence_score = confidence * 15

            score = discount_score + quality_score + rl_score + urgency_score + confidence_score
            score = max(0, min(100, score))

            results.append({
                "offer": offer,
                "deal_score": round(score, 1),
                "breakdown": {
                    "discount_score": round(discount_score, 1),
                    "quality_score": round(quality_score, 1),
                    "rate_limit_score": round(rl_score, 1),
                    "urgency_score": round(urgency_score, 1),
                    "confidence_score": round(confidence_score, 1),
                },
            })
        except Exception as exc:
            logger.error("Failed to score offer: %s", exc)
            results.append({"offer": offer, "deal_score": 0, "breakdown": {}})

    results.sort(key=lambda x: x["deal_score"], reverse=True)
    logger.info("Scored %d deals, top score: %.1f", len(results), results[0]["deal_score"] if results else 0)
    return results
