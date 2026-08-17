"""app/sources/base.py — Base source adapter protocol and observation dataclass."""
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


class SourceAdapter(Protocol):
    source_id: str
    cadence_minutes: int

    def fetch(self) -> list[Observation]: ...
    def extract(self, observation: Observation) -> list[OfferSnapshot]: ...


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
