"""app/sources/hf_router.py — HuggingFace Inference Providers adapter.

One key, hundreds of models, per-provider pricing, auto-failover.
The single best add per PROVIDER-REFERENCE.md.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "hf-router"
CADENCE_MINUTES = 1440  # 24h
API_URL = "https://router.huggingface.co/v1/models"


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
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    for m in data.get("data", []):
        mid = m.get("id", "")
        providers = m.get("providers", [])

        for p in providers:
            if p.get("status") != "live":
                continue
            pricing = p.get("pricing") or {}
            in_price = float(pricing.get("input") or 0)
            out_price = float(pricing.get("output") or 0)
            is_free = bool(p.get("is_free"))

            offers.append(OfferSnapshot(
                provider_id=p.get("provider", "huggingface"),
                model_id=mid,
                provider_model_slug=mid,
                offer_kind="free_tier" if is_free else "provider_route",
                input_per_m=in_price * 1e6 if in_price < 1 else in_price,
                output_per_m=out_price * 1e6 if out_price < 1 else out_price,
                free=is_free,
                context_tokens=p.get("context_length"),
                metadata={
                    "source_url": observation.url,
                    "latency_ms": p.get("first_token_latency_ms"),
                    "throughput_tps": p.get("throughput"),
                    "hf_provider": p.get("provider"),
                    "supports_tools": p.get("supports_tools"),
                    "supports_structured_output": p.get("supports_structured_output"),
                }))
    return offers
