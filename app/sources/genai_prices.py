"""app/sources/genai_prices.py — pydantic/genai-prices adapter.

Provides provider extraction patterns and pricing URLs.
"""
from __future__ import annotations

import json
from pathlib import Path
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "genai-prices"
CADENCE_MINUTES = 1440
DATA_FILE = Path(__file__).resolve().parents[3] / "genai-prices" / "prices" / "data.json"


def fetch() -> list[Observation]:
    if not DATA_FILE.exists():
        return [Observation(source_id=SOURCE_ID, source_type="local_file", url=str(DATA_FILE),
                            fetched_at=now_iso(), status=None, text="FILE_NOT_FOUND", sha256="none")]
    try:
        text = DATA_FILE.read_text(encoding="utf-8")
        return [Observation(source_id=SOURCE_ID, source_type="local_file", url=str(DATA_FILE),
                            fetched_at=now_iso(), status=200, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="local_file", url=str(DATA_FILE),
                            fetched_at=now_iso(), status=None, text=f"READ_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or observation.text.startswith(("FILE_NOT_FOUND", "READ_ERROR")):
        return []
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    for provider in data:
        if not isinstance(provider, dict):
            continue
        provider_id = provider.get("id", provider.get("name", "unknown"))
        name = provider.get("name", provider_id)
        pricing_urls = provider.get("pricing_urls", [])
        api_pattern = provider.get("api_pattern", "")

        offers.append(OfferSnapshot(
            provider_id=provider_id,
            model_id=f"{provider_id}/all",
            provider_model_slug=f"{provider_id}/extraction-pattern",
            offer_kind="provider_pattern",
            metadata={
                "source": "genai-prices",
                "name": name,
                "pricing_urls": pricing_urls,
                "api_pattern": api_pattern,
                "model_match": provider.get("model_match", {}),
                "provider_match": provider.get("provider_match", {}),
            },
        ))

    return offers
