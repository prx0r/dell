"""Economic semantics for Oracle-1.

Free has multiple meanings:
- ZERO_MARGINAL_PRICE
- FREE_QUOTA
- TRIAL_CREDIT
- PROMOTIONAL_QUOTA
- SUBSCRIPTION_INCLUDED
- CONDITIONAL_FREE
- COMMUNITY_COMPUTE
- PAID
- UNKNOWN
"""
from __future__ import annotations

import json
from typing import Optional


# Economic access classes
ACCESS_CLASSES = {
    "ZERO_MARGINAL_PRICE": "Truly free, no limits",
    "FREE_QUOTA": "Free up to a limit (RPD, tokens, etc.)",
    "TRIAL_CREDIT": "Free credits for new accounts",
    "PROMOTIONAL_QUOTA": "Limited-time free quota",
    "SUBSCRIPTION_INCLUDED": "Free as part of paid subscription",
    "CONDITIONAL_FREE": "Free under certain conditions",
    "COMMUNITY_COMPUTE": "Free via community/shared compute",
    "PAID": "Not free",
    "UNKNOWN": "Free status unknown",
}


class QuotaObject:
    """Structured quota representation."""
    
    def __init__(self, quantity: int, unit: str, window_kind: str,
                 window_duration_seconds: int, scope: str = "account",
                 conditions: dict = None):
        self.quantity = quantity
        self.unit = unit  # request, token, credit, compute-unit
        self.window_kind = window_kind  # rolling, fixed, billing-cycle
        self.window_duration_seconds = window_duration_seconds
        self.scope = scope  # account, key, model, endpoint, ip
        self.conditions = conditions or {}
    
    def to_dict(self) -> dict:
        return {
            "quantity": self.quantity,
            "unit": self.unit,
            "window": {
                "kind": self.window_kind,
                "duration_seconds": self.window_duration_seconds,
            },
            "scope": self.scope,
            "conditions": self.conditions,
        }
    
    @classmethod
    def from_rpd(cls, rpd: int) -> "QuotaObject":
        """Create from requests per day."""
        return cls(rpd, "request", "fixed", 86400)
    
    @classmethod
    def from_rph(cls, rph: int, window_hours: int = 5) -> "QuotaObject":
        """Create from requests per hour/window."""
        return cls(rph, "request", "rolling", window_hours * 3600)
    
    @classmethod
    def from_tpd(cls, tpd: int) -> "QuotaObject":
        """Create from tokens per day."""
        return cls(tpd, "token", "fixed", 86400)


def classify_economic_access(offer: dict) -> str:
    """Classify the economic access type for an offer."""
    free = offer.get("free")
    
    # None/unknown should be UNKNOWN, not PAID
    if free is None:
        return "UNKNOWN"
    
    if not free:
        return "PAID"
    
    # Check for quota
    rpd = offer.get("requests_per_day")
    rph = offer.get("requests_per_5h")
    
    if rpd or rph:
        return "FREE_QUOTA"
    
    # Check for credits
    credits = offer.get("credits_included")
    if credits and credits > 0:
        return "TRIAL_CREDIT"
    
    # Check for subscription
    sub = offer.get("subscription_usd")
    if sub and sub > 0:
        return "SUBSCRIPTION_INCLUDED"
    
    # Check for usage multiplier (promo)
    mult = offer.get("usage_multiplier")
    if mult and mult > 1:
        return "PROMOTIONAL_QUOTA"
    
    # Check for conditional
    region = offer.get("region")
    requires_card = offer.get("requires_card")
    requires_kyc = offer.get("requires_kyc")
    
    if region or requires_card or requires_kyc:
        return "CONDITIONAL_FREE"
    
    # Default to free quota
    return "FREE_QUOTA"


def get_quota_display(quota: QuotaObject) -> str:
    """Get human-readable quota display."""
    if quota.window_kind == "fixed":
        return "%d %ss/day" % (quota.quantity, quota.unit)
    elif quota.window_kind == "rolling":
        hours = quota.window_duration_seconds // 3600
        return "%d %ss/%dh rolling" % (quota.quantity, quota.unit, hours)
    else:
        return "%d %ss" % (quota.quantity, quota.unit)


def calculate_effective_cost(offer: dict, task_tokens: int) -> float:
    """Calculate effective cost for a workload."""
    if offer.get("free"):
        return 0.0
    
    input_per_m = offer.get("input_per_m")
    output_per_m = offer.get("output_per_m")
    
    if input_per_m is None:
        return float('inf')
    
    # Assume 50% input, 50% output
    input_tokens = task_tokens * 0.5
    output_tokens = task_tokens * 0.5
    
    cost = (input_per_m * input_tokens + (output_per_m or 0) * output_tokens) / 1_000_000
    return cost
