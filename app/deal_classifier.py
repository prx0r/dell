"""Classify offers as deals vs catalog.

A deal is an UNUSUALLY favorable inference opportunity.
A catalog entry is ordinary market-rate.
"""
from __future__ import annotations

from typing import Optional


DEAL_TYPES = {
    "PROMO_PRICE", "TEMPORARY_FREE", "USAGE_MULTIPLIER", "QUOTA_BOOST",
    "NEW_USER_CREDIT", "TRIAL_CREDIT", "STARTUP_CREDIT", "RESEARCH_CREDIT",
    "SUBSCRIPTION_ALLOWANCE", "BATCH_DISCOUNT", "OFF_PEAK_DISCOUNT",
    "BETA_FREE", "REFERRAL_CREDIT", "REGIONAL_DISCOUNT", "PRICE_ANOMALY",
    "PROVIDER_ARBITRAGE",
}


def classify_as_deal(offer: dict) -> dict:
    """Classify an offer as deal or catalog."""
    deal_type = offer.get("deal_type") or offer.get("metadata", {}).get("offer_kind", "")
    is_free = offer.get("free", False)
    usage_mult = offer.get("usage_multiplier") or offer.get("metadata", {}).get("multiplier")
    cap_ratio = offer.get("metadata", {}).get("capacity_ratio_vs_median")

    # Check if it's a deal
    is_deal = False
    deal_reasons = []

    if deal_type in DEALAL_TYPES:
        is_deal = True
        deal_reasons.append(f"deal_type={deal_type}")

    if usage_mult and usage_mult >= 2:
        is_deal = True
        deal_reasons.append(f"usage_multiplier={usage_mult}")

    if cap_ratio and cap_ratio >= 3:
        is_deal = True
        deal_reasons.append(f"capacity_ratio={cap_ratio}")

    if is_free:
        # Free is only a deal if it's unusual (high quota, large context, etc.)
        ctx = offer.get("context_tokens") or 0
        rpd = offer.get("requests_per_day") or offer.get("metadata", {}).get("requests_per_5h")
        if ctx >= 1000000 or (rpd and rpd >= 1000):
            is_deal = True
            deal_reasons.append(f"high-value free (ctx={ctx}, rpd={rpd})")

    if not is_deal:
        deal_reasons.append("ordinary market-rate")

    return {
        "is_deal": is_deal,
        "deal_type": deal_type if is_deal else "CATALOG",
        "deal_reasons": deal_reasons,
    }


# Map of deal_type values
DEALAL_TYPES = {
    "PROMO_PRICE", "TEMPORARY_FREE", "USAGE_MULTIPLIER", "QUOTA_BOOST",
    "NEW_USER_CREDIT", "TRIAL_CREDIT", "STARTUP_CREDIT", "RESEARCH_CREDIT",
    "SUBSCRIPTION_ALLOWANCE", "BATCH_DISCOUNT", "OFF_PEAK_DISCOUNT",
    "BETA_FREE", "REFERRAL_CREDIT", "REGIONAL_DISCOUNT", "PRICE_ANOMALY",
    "PROVIDER_ARBITRAGE",
    "free_tier", "usage_multiplier", "capacity_multiplier",  # from adapters
}
