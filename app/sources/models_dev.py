"""app/sources/models_dev.py — models.dev adapter.

Rich data: capabilities, benchmarks, modalities, context, release dates.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "models-dev"
CADENCE_MINUTES = 1440  # 24h
API_URL = "https://models.dev/models.json"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        text = resp.read().decode("utf-8")
        return [Observation(source_id=SOURCE_ID, source_type="api_json", url=API_URL,
                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="api_json", url=API_URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []
    offers = []
    for mid, rec in data.items():
        if not isinstance(rec, dict):
            continue
        price = rec.get("pricing", {})
        in_ = float(price.get("input") or 0) if isinstance(price, dict) else 0
        out_ = float(price.get("output") or 0) if isinstance(price, dict) else 0
        limit = rec.get("limit") or {}
        offers.append(OfferSnapshot(
            provider_id=mid.split("/")[0], model_id=mid, provider_model_slug=mid,
            offer_kind="metered_api", input_per_m=in_, output_per_m=out_,
            free=(in_ == 0 and out_ == 0),
            context_tokens=limit.get("context") if isinstance(limit, dict) else None,
            metadata={
                "source_url": observation.url,
                "modalities": rec.get("modalities", {}),
                "benchmarks": rec.get("benchmarks", []),
                "description": rec.get("description", ""),
                "reasoning": rec.get("reasoning", False),
                "tool_call": rec.get("tool_call", False),
                "structured_output": rec.get("structured_output", False),
                "open_weights": rec.get("open_weights", False),
                "release_date": rec.get("release_date", ""),
                "last_updated": rec.get("last_updated", ""),
                "family": rec.get("family", ""),
                "temperature": rec.get("temperature", False),
            }))
    return offers
