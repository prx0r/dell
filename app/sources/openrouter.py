"""app/sources/openrouter.py — OpenRouter adapter.

Fetches the OpenRouter models API for catalog, prices, free variants, context.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "openrouter-models"
CADENCE_MINUTES = 360  # 6h

API_URL = "https://openrouter.ai/api/v1/models"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(API_URL, headers={
            "User-Agent": "deal-radar/2.0",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=30)
        text = resp.read().decode("utf-8")
        return [Observation(
            source_id=SOURCE_ID, source_type="api_json",
            url=API_URL, fetched_at=now_iso(), status=resp.status,
            text=text, sha256=sha256(text),
        )]
    except Exception as e:
        return [Observation(
            source_id=SOURCE_ID, source_type="api_json",
            url=API_URL, fetched_at=now_iso(), status=None,
            text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)),
        )]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    for m in data.get("data", []):
        mid = m.get("id", "")
        pricing = m.get("pricing", {})
        try:
            in_price = float(pricing.get("prompt") or 0)
            out_price = float(pricing.get("completion") or 0)
        except (TypeError, ValueError):
            continue

        cache_read = 0.0
        try:
            cache_read = float(pricing.get("input_cache_read") or 0)
        except (TypeError, ValueError):
            pass

        is_free = ":free" in mid or (in_price == 0 and out_price == 0)

        offers.append(OfferSnapshot(
            provider_id="openrouter",
            model_id=mid,
            provider_model_slug=mid,
            offer_kind="free_tier" if is_free else "provider_route",
            input_per_m=in_price * 1e6 if in_price < 1 else in_price,
            output_per_m=out_price * 1e6 if out_price < 1 else out_price,
            cache_read_per_m=cache_read * 1e6 if cache_read < 1 else cache_read,
            free=is_free,
            context_tokens=m.get("context_length"),
            metadata={
                "source_url": observation.url,
                "top_provider": m.get("top_provider", {}),
                "architecture": m.get("architecture", {}),
            },
        ))
    return offers
