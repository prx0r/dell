"""app/models_v2.py — The canonical data model.

Four objects, strictly separated:

  Model → ProviderOffering → CommercialOffer → DealEvent

This is THE schema. Everything else derives from it.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# --- Model ---

@dataclass
class Model:
    """A model identity. Permanent-ish. Same model across providers."""
    model_id: str  # e.g. "xiaomi/mimo-v2.5"
    canonical_name: str
    family: str | None = None
    author: str | None = None
    context_tokens: int | None = None
    max_output_tokens: int | None = None
    # Capabilities (soft data — evidence, not truth)
    reasoning: bool = False
    tool_calling: bool = False
    structured_output: bool = False
    vision: bool = False
    open_weights: bool = False
    # Derived scores (versioned formulas)
    intelligence_score: float | None = None
    coding_score: float | None = None
    agentic_score: float | None = None
    speed_score: float | None = None
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    metadata: dict = field(default_factory=dict)


# --- ProviderOffering ---

@dataclass
class ProviderOffering:
    """A specific provider's offering of a model. Separate from the model identity."""
    offering_id: str  # e.g. "opencode-zen:xiaomi/mimo-v2.5"
    provider_id: str
    model_id: str
    provider_model_slug: str | None = None
    # What you get
    openai_compatible: bool = True
    anthropic_compatible: bool = False
    # Rate limits
    requests_per_minute: int | None = None
    requests_per_day: int | None = None
    tokens_per_day: int | None = None
    # Regional
    regions: list[str] = field(default_factory=lambda: ["global"])
    kyc_required: bool = False
    phone_required: bool = False
    card_required: bool = False
    # Terms
    automation_allowed: bool = True
    production_allowed: bool = True
    # Metadata
    created_at: str = ""
    metadata: dict = field(default_factory=dict)


# --- CommercialOffer ---

@dataclass
class CommercialOffer:
    """How someone can buy access. The pricing/plan layer."""
    offer_id: str  # e.g. "opencode-zen:xiaomi/mimo-v2.5:free"
    offering_id: str
    offer_type: str  # free_tier, payg, subscription, credit_pack, batch, off_peak
    # Pricing
    input_per_m_tokens: float | None = None
    output_per_m_tokens: float | None = None
    cache_read_per_m_tokens: float | None = None
    cache_write_per_m_tokens: float | None = None
    # Subscription
    subscription_usd_monthly: float | None = None
    included_credits_usd: float | None = None
    credit_bonus: float | None = None  # e.g. 1.10 = 10% bonus
    # Batch/off-peak
    batch_discount: float | None = None  # e.g. 0.5 = 50% off
    off_peak_discount: float | None = None
    off_peak_hours: str | None = None  # e.g. "22:00-06:00 UTC"
    # Quota
    free_requests_per_day: int | None = None
    free_tokens_per_period: int | None = None
    free_period: str | None = None  # "day", "month", "one_time"
    # Status
    active: bool = True
    starts_at: str | None = None
    ends_at: str | None = None
    # Metadata
    created_at: str = ""
    metadata: dict = field(default_factory=dict)


# --- DealEvent ---

@dataclass
class DealEvent:
    """A temporal deal event. Immutable-ish historical evidence.

    Status lifecycle:
      DISCOVERED → VERIFIED → MODIFIED → EXPIRED → RESTORED
    """
    event_id: str  # content-addressed: provider:model:type:timestamp
    provider_id: str
    event_type: str  # free_started, price_drop, promo_started, promo_ended,
                     # usage_multiplier, credit_granted, quota_changed, etc.
    model_id: str | None = None
    offering_id: str | None = None
    offer_id: str | None = None
    status: str = "active"  # active, expired, modified, restored
    # What changed
    benefit: dict = field(default_factory=dict)  # type-specific benefit description
    previous_value: dict | None = None
    current_value: dict | None = None
    # Eligibility
    eligibility: dict = field(default_factory=dict)
    # Restrictions
    restrictions: dict = field(default_factory=dict)
    # Timing
    starts_at: str | None = None
    ends_at: str | None = None
    # Source provenance
    source_url: str = ""
    source_type: str = ""  # official_docs, official_api, changelog, blog, community, reddit
    source_language: str = "en"
    official: bool = False
    observed_at: str = ""
    # Verification
    confidence: float = 0.0  # 0-1
    verification_status: str = "unverified"  # verified, likely, community_reported, unverified
    last_checked_at: str = ""
    # History
    created_at: str = ""
    updated_at: str = ""
    superseded_by: str | None = None
    metadata: dict = field(default_factory=dict)


# --- Derived Economics (computed, not stored) ---

@dataclass
class DerivedEconomics:
    """Computed economics for a model×provider×offer combination."""
    model_id: str
    provider_id: str
    offer_id: str
    # Nominal
    nominal_input_per_m: float | None = None
    nominal_output_per_m: float | None = None
    # Effective (with all discounts/credits applied)
    effective_input_per_m: float | None = None
    effective_output_per_m: float | None = None
    # Batch/off-peak
    batch_effective_input: float | None = None
    offpeak_effective_input: float | None = None
    # Free quota value
    free_quota_value_usd: float | None = None
    credit_value_usd: float | None = None
    deal_savings_percent: float | None = None
    # Standardized task costs
    cost_per_short_chat: float | None = None
    cost_per_coding_task: float | None = None
    cost_per_rag_query: float | None = None
    cost_per_10m_tokens: float | None = None
    cost_per_agent_session: float | None = None


# --- Source Provenance ---

@dataclass
class SourceRecord:
    """A source observation. Never overwritten."""
    source_id: str
    source_type: str
    url: str
    fetched_at: str
    http_status: int | None = None
    content_hash: str = ""
    language: str = "en"
    official: bool = False
    extraction_status: str = "pending"  # pending, extracted, error
    metadata: dict = field(default_factory=dict)


# --- Workload Presets ---

WORKLOAD_PRESETS = {
    "short_chat": {"input_tokens": 500, "output_tokens": 300, "requests": 50, "description": "Quick questions, chat"},
    "coding_agent": {"input_tokens": 8000, "output_tokens": 3000, "requests": 100, "description": "Code generation, debugging"},
    "rag": {"input_tokens": 3000, "output_tokens": 1000, "requests": 200, "description": "Retrieval-augmented generation"},
    "bulk_extraction": {"input_tokens": 2000, "output_tokens": 500, "requests": 1000, "description": "Data extraction at scale"},
    "translation": {"input_tokens": 3000, "output_tokens": 3000, "requests": 200, "description": "Translation tasks"},
    "long_context_research": {"input_tokens": 50000, "output_tokens": 10000, "requests": 20, "description": "Research synthesis over large documents"},
}


def compute_derived_economics(offer: CommercialOffer, model: Model = None) -> DerivedEconomics:
    """Compute derived economics from a commercial offer."""
    econ = DerivedEconomics(
        model_id=model.model_id if model else "",
        provider_id="",
        offer_id=offer.offer_id,
        nominal_input_per_m=offer.input_per_m_tokens,
        nominal_output_per_m=offer.output_per_m_tokens,
    )

    # Effective costs (with batch/off-peak discounts)
    if offer.batch_discount and offer.input_per_m_tokens:
        econ.batch_effective_input = offer.input_per_m_tokens * (1 - offer.batch_discount)
    if offer.off_peak_discount and offer.input_per_m_tokens:
        econ.offpeak_effective_input = offer.input_per_m_tokens * (1 - offer.off_peak_discount)

    # Free quota value
    if offer.free_tokens_per_period and offer.input_per_m_tokens:
        econ.free_quota_value_usd = offer.free_tokens_per_period * offer.input_per_m_tokens / 1_000_000

    # Standardized task costs
    for preset_name, preset in WORKLOAD_PRESETS.items():
        input_cost = (offer.input_per_m_tokens or 0) * preset["input_tokens"] / 1_000_000 * preset["requests"]
        output_cost = (offer.output_per_m_tokens or 0) * preset["output_tokens"] / 1_000_000 * preset["requests"]
        total = input_cost + output_cost
        setattr(econ, f"cost_per_{preset_name}", round(total, 6))

    return econ
