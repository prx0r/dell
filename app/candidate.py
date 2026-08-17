"""Typed CandidateOffer for round-trip validation.

Every adapter must return this shape. No manual dictionary plumbing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import hashlib
import json


@dataclass
class CandidateOffer:
    """Canonical candidate from an adapter. Validated before DB commit."""
    provider_id: str
    model_id: Optional[str] = None
    offer_type: str = "metered_api"
    # Pricing
    input_per_m: Optional[float] = None
    output_per_m: Optional[float] = None
    cache_read_per_m: Optional[float] = None
    # Free tier
    free: Optional[bool] = None  # None = unknown
    price_state: str = "unknown"  # FREE / PAID / UNKNOWN
    # Quota (preserved, not collapsed)
    requests_per_day: Optional[int] = None
    requests_per_5h: Optional[int] = None
    requests_per_minute: Optional[int] = None
    tokens_per_day: Optional[int] = None
    quota_scope: Optional[str] = None
    quota_window_hours: Optional[float] = None
    # Subscription
    subscription_usd: Optional[float] = None
    credits_included: Optional[float] = None
    usage_multiplier: Optional[float] = None
    # Context
    context_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    # Eligibility
    region: Optional[str] = None
    automation_allowed: Optional[bool] = None
    requires_card: Optional[bool] = None
    requires_phone: Optional[bool] = None
    requires_kyc: Optional[bool] = None
    # Timing
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None
    # Classification
    deal_type: Optional[str] = None
    deal_status: str = "active"
    # Provenance
    source_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_db_dict(self) -> dict:
        """Convert to dict for DB insertion."""
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "offer_type": self.offer_type,
            "input_per_m": self.input_per_m,
            "output_per_m": self.output_per_m,
            "cache_read_per_m": self.cache_read_per_m,
            "free": int(self.free) if self.free is not None else None,
            "price_state": self.price_state,
            "requests_per_day": self.requests_per_day,
            "requests_per_5h": self.requests_per_5h,
            "requests_per_minute": self.requests_per_minute,
            "tokens_per_day": self.tokens_per_day,
            "quota_scope": self.quota_scope,
            "quota_window_hours": self.quota_window_hours,
            "subscription_usd": self.subscription_usd,
            "credits_included": self.credits_included,
            "usage_multiplier": self.usage_multiplier,
            "context_tokens": self.context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "region": self.region,
            "automation_allowed": int(self.automation_allowed) if self.automation_allowed is not None else None,
            "requires_card": int(self.requires_card) if self.requires_card is not None else None,
            "requires_phone": int(self.requires_phone) if self.requires_phone is not None else None,
            "requires_kyc": int(self.requires_kyc) if self.requires_kyc is not None else None,
            "starts_at": self.starts_at,
            "expires_at": self.expires_at,
            "deal_type": self.deal_type,
            "deal_status": self.deal_status,
            "source_url": self.source_url,
            "metadata_json": json.dumps(self.metadata),
        }

    @classmethod
    def from_snapshot(cls, snapshot) -> "CandidateOffer":
        """Convert OfferSnapshot to CandidateOffer."""
        meta = snapshot.__dict__ if hasattr(snapshot, '__dict__') else snapshot
        return cls(
            provider_id=meta.get("provider_id", ""),
            model_id=meta.get("model_id"),
            offer_type=meta.get("offer_kind", "metered_api"),
            input_per_m=meta.get("input_per_m"),
            output_per_m=meta.get("output_per_m"),
            cache_read_per_m=meta.get("cache_read_per_m"),
            free=meta.get("free"),
            price_state="FREE" if meta.get("free") else ("PAID" if meta.get("input_per_m") else "UNKNOWN"),
            requests_per_day=meta.get("requests_per_day"),
            requests_per_5h=meta.get("metadata", {}).get("requests_per_5h"),
            requests_per_minute=meta.get("requests_minute"),
            tokens_per_day=meta.get("tokens_day"),
            quota_scope=meta.get("metadata", {}).get("scope"),
            quota_window_hours=meta.get("metadata", {}).get("window_hours"),
            usage_multiplier=meta.get("usage_multiplier") or meta.get("metadata", {}).get("multiplier"),
            context_tokens=meta.get("context_tokens"),
            max_output_tokens=meta.get("max_output_tokens"),
            region=None,  # Always unknown
            automation_allowed=meta.get("metadata", {}).get("automation_allowed"),
            deal_type=meta.get("offer_kind"),
            source_url=meta.get("metadata", {}).get("source_url"),
            metadata=meta.get("metadata", {}),
        )
