"""app/sources/__init__.py — Base source adapter protocol and observation dataclass."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Observation:
    source_id: str
    source_type: str
    url: str
    fetched_at: str
    status: int | None
    text: str
    sha256: str
    etag: str | None = None
    last_modified: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class OfferSnapshot:
    provider_id: str
    model_id: str | None
    provider_model_slug: str | None
    offer_kind: str  # metered_api, provider_route, free_tier, temporary_free, subscription_allowance, etc
    input_per_m: float | None = None
    output_per_m: float | None = None
    cache_read_per_m: float | None = None
    free: bool = False
    requests_day: int | None = None
    requests_month: int | None = None
    tokens_day: int | None = None
    context_tokens: int | None = None
    usage_multiplier: float | None = None
    subscription_usd: float | None = None
    credits_included: float | None = None
    starts_at: str | None = None
    expires_at: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON output."""
        d = {}
        for k, v in self.__dict__.items():
            if v is not None and v != {} and v != False:
                d[k] = v
        return d


class SourceAdapter(Protocol):
    source_id: str
    cadence_minutes: int

    def fetch(self) -> list[Observation]: ...
    def extract(self, observation: Observation) -> list[OfferSnapshot]: ...


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def run_promo_extraction(observation: Observation, offers: list[OfferSnapshot]) -> list[OfferSnapshot]:
    """Run promo_extract.py on observation text and attach promotion signals to offers.
    
    This wires the standalone promo extraction engine into the adapter pipeline.
    Call this after extract() to enrich offers with promotion detection.
    """
    try:
        from promo_extract import extract_promotions
        promotions = extract_promotions(observation.text, observation.source_id)
        if promotions and offers:
            # Attach promotion signals to the first offer (or create one if empty)
            promo_data = {
                "promotions_found": len(promotions),
                "promo_types": list(set(p["event_type"] for p in promotions)),
                "max_confidence": max(p["confidence"] for p in promotions),
            }
            if offers:
                offers[0].metadata["promo_signals"] = promo_data
            else:
                # Generate synthetic model_id for promo signals
                import hashlib
                url_hash = hashlib.md5(observation.url.encode()).hexdigest()[:8]
                synthetic_model_id = f"promo-{url_hash}"
                
                offers.append(OfferSnapshot(
                    provider_id=observation.source_id,
                    model_id=synthetic_model_id,
                    provider_model_slug=None,
                    offer_kind="promo_signal",
                    metadata={**promo_data, "source_url": observation.url}
                ))
        return offers
    except ImportError:
        return offers
