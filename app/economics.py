"""Billing model calculations for offer cost comparison."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def effective_cost(offer: dict, workload: dict) -> float:
    """Calculate effective cost per job for an offer given a workload profile.

    Supported billing models:
        - metered_api: Pay per token/request
        - subscription_allowance: Monthly sub with included quota
        - credit_pack: Prepaid credit balance
        - free_tier: Free with limits
        - temporary_free: Free for a limited time
        - off_peak: Discounted during off-peak hours
        - batch: Batch processing discount

    Args:
        offer: Offer dict with billing model and pricing info.
        workload: Workload dict with tokens_per_job, jobs_per_day, etc.

    Returns:
        Effective cost per job in USD.
    """
    model = offer.get("billing_model", "metered_api")
    tokens_per_job = workload.get("tokens_per_job", 1000)
    jobs_per_day = workload.get("jobs_per_day", 10)
    cache_hit_rate = workload.get("cache_hit_rate", 0.0)

    effective_tokens = tokens_per_job * (1 - cache_hit_rate)

    try:
        if model == "metered_api":
            return _cost_metered(offer, effective_tokens)
        elif model == "subscription_allowance":
            return _cost_subscription(offer, effective_tokens, jobs_per_day)
        elif model == "credit_pack":
            return _cost_credit_pack(offer, effective_tokens)
        elif model == "free_tier":
            return _cost_free_tier(offer, effective_tokens)
        elif model == "temporary_free":
            return _cost_temporary_free(offer, effective_tokens)
        elif model == "off_peak":
            return _cost_off_peak(offer, effective_tokens)
        elif model == "batch":
            return _cost_batch(offer, effective_tokens)
        else:
            logger.warning("Unknown billing model: %s, defaulting to metered", model)
            return _cost_metered(offer, effective_tokens)
    except Exception as exc:
        logger.error("Failed to calculate cost for model %s: %s", model, exc)
        return float("inf")


def _cost_metered(offer: dict, tokens: float) -> float:
    price_per_mtok = offer.get("price_per_mtok", 0)
    price_per_1k = offer.get("price_per_1k_requests", 0)
    input_price = offer.get("input_price_per_mtok", price_per_mtok)
    output_price = offer.get("output_price_per_mtok", price_per_mtok * 3)

    input_ratio = offer.get("input_output_ratio", 0.3)
    input_tokens = tokens * input_ratio
    output_tokens = tokens * (1 - input_ratio)

    cost = (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)
    return max(cost, 0.0001)


def _cost_subscription(offer: dict, tokens: float, jobs_per_day: int) -> float:
    monthly_price = offer.get("price_usd", 0)
    included_tokens = offer.get("included_tokens_per_month", 0)
    overage_per_mtok = offer.get("overage_per_mtok", 0)
    days_per_month = 30

    monthly_tokens_needed = tokens * jobs_per_day * days_per_month

    if included_tokens <= 0:
        return 0 if monthly_price == 0 else monthly_price / (jobs_per_day * days_per_month)

    if monthly_tokens_needed <= included_tokens:
        return monthly_price / (jobs_per_day * days_per_month)

    overage_tokens = monthly_tokens_needed - included_tokens
    overage_cost = (overage_tokens / 1_000_000) * overage_per_mtok
    total_monthly = monthly_price + overage_cost
    return total_monthly / (jobs_per_day * days_per_month)


def _cost_credit_pack(offer: dict, tokens: float) -> float:
    credit_cost_usd = offer.get("credit_cost_usd", 0)
    credits_per_dollar = offer.get("credits_per_dollar", 1000)
    tokens_per_credit = offer.get("tokens_per_credit", 1000)

    if credits_per_dollar <= 0 or tokens_per_credit <= 0:
        return float("inf")

    cost_per_token = credit_cost_usd / (credits_per_dollar * tokens_per_credit)
    return max(cost_per_token * tokens, 0.0001)


def _cost_free_tier(offer: dict, tokens: float) -> float:
    daily_limit = offer.get("daily_token_limit", 0)
    monthly_limit = offer.get("monthly_token_limit", 0)

    if daily_limit > 0 and tokens <= daily_limit:
        return 0.0
    if monthly_limit > 0 and tokens * 30 <= monthly_limit:
        return 0.0

    overage_price = offer.get("overage_per_mtok", 0)
    if overage_price > 0:
        return (tokens / 1_000_000) * overage_price

    return float("inf")


def _cost_temporary_free(offer: dict, tokens: float) -> float:
    free_until = offer.get("free_until")
    if free_until:
        return 0.0

    regular_price = offer.get("regular_price_per_mtok", 0)
    return (tokens / 1_000_000) * regular_price if regular_price > 0 else float("inf")


def _cost_off_peak(offer: dict, tokens: float) -> float:
    peak_price = offer.get("peak_price_per_mtok", 0)
    off_peak_price = offer.get("off_peak_price_per_mtok", 0)
    off_peak_ratio = offer.get("off_peak_usage_ratio", 0.5)

    peak_cost = (tokens * (1 - off_peak_ratio) / 1_000_000) * peak_price
    off_peak_cost = (tokens * off_peak_ratio / 1_000_000) * off_peak_price
    return max(peak_cost + off_peak_cost, 0.0001)


def _cost_batch(offer: dict, tokens: float) -> float:
    standard_price = offer.get("standard_price_per_mtok", 0)
    batch_discount = offer.get("batch_discount_percent", 0)
    batch_latency_sla = offer.get("batch_latency_sla_seconds", 0)

    discounted_price = standard_price * (1 - batch_discount / 100)
    cost = (tokens / 1_000_000) * discounted_price
    return max(cost, 0.0001)


def compare_offers(offers: list[dict], workload: dict) -> list[dict]:
    """Compare effective costs across multiple offers for a given workload.

    Args:
        offers: List of offer dicts.
        workload: Workload dict with tokens_per_job, jobs_per_day, etc.

    Returns:
        List of dicts sorted by cost (ascending) with 'offer' and 'cost_per_job' keys.
    """
    if not offers:
        return []

    results = []
    for offer in offers:
        try:
            cost = effective_cost(offer, workload)
            daily_cost = cost * workload.get("jobs_per_day", 1)
            monthly_cost = daily_cost * 30

            results.append({
                "offer": offer,
                "cost_per_job": round(cost, 6),
                "daily_cost": round(daily_cost, 4),
                "monthly_cost": round(monthly_cost, 2),
                "billing_model": offer.get("billing_model", "unknown"),
            })
        except Exception as exc:
            logger.error("Failed to evaluate offer '%s': %s", offer.get("name", "unknown"), exc)
            results.append({
                "offer": offer,
                "cost_per_job": float("inf"),
                "daily_cost": float("inf"),
                "monthly_cost": float("inf"),
                "billing_model": offer.get("billing_model", "unknown"),
            })

    results.sort(key=lambda x: x["cost_per_job"])
    logger.info("Compared %d offers, cheapest: $%.6f/job", len(results), results[0]["cost_per_job"] if results else 0)
    return results
