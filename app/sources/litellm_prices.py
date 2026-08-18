"""app/sources/litellm_prices.py — litellm model_prices_and_context_window.json adapter.

Extracts ALL available data: pricing tiers, capabilities, regions, deprecation,
batch/priority/audio/video pricing, supports flags, and more.
"""
from __future__ import annotations

import json
from pathlib import Path
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "litellm-prices"
CADENCE_MINUTES = 1440
LITELLM_REPO = Path(__file__).resolve().parents[3] / "litellm"
PRICES_FILE = LITELLM_REPO / "model_prices_and_context_window.json"


def fetch() -> list[Observation]:
    if not PRICES_FILE.exists():
        return [Observation(source_id=SOURCE_ID, source_type="local_file", url=str(PRICES_FILE),
                            fetched_at=now_iso(), status=None, text="FILE_NOT_FOUND", sha256="none")]
    try:
        text = PRICES_FILE.read_text(encoding="utf-8")
        return [Observation(source_id=SOURCE_ID, source_type="local_file", url=str(PRICES_FILE),
                            fetched_at=now_iso(), status=200, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="local_file", url=str(PRICES_FILE),
                            fetched_at=now_iso(), status=None, text=f"READ_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or observation.text.startswith(("FILE_NOT_FOUND", "READ_ERROR")):
        return []
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    for model_id, rec in data.items():
        if not isinstance(rec, dict):
            continue
        if "max input tokens" in str(rec.get("max_input_tokens", "")):
            continue

        # Core pricing
        input_cost = rec.get("input_cost_per_token")
        output_cost = rec.get("output_cost_per_token")
        cache_read = rec.get("cache_read_input_token_cost")
        cache_creation = rec.get("cache_creation_input_token_cost")
        batch_input = rec.get("input_cost_per_token_batches")
        batch_output = rec.get("output_cost_per_token_batches")
        priority_input = rec.get("input_cost_per_token_priority")
        priority_output = rec.get("output_cost_per_token_priority")
        reasoning_output = rec.get("output_cost_per_reasoning_token")

        # Token limits
        max_input = rec.get("max_input_tokens") or rec.get("max_tokens")
        max_output = rec.get("max_output_tokens")

        # Rate limits
        rpm = rec.get("rpm")
        tpm = rec.get("tpm")

        # Free check
        free = (input_cost == 0 or input_cost is None) and (output_cost == 0 or output_cost is None)

        # Capabilities (all supports_* flags)
        supports = []
        for key in rec:
            if key.startswith("supports_") and rec[key]:
                supports.append(key.replace("supports_", ""))

        # Build comprehensive metadata
        metadata = {
            "source": "litellm",
            "mode": rec.get("mode", "chat"),
            "max_output_tokens": max_output,
            "deprecation_date": rec.get("deprecation_date"),
            "supported_regions": rec.get("supported_regions"),
            "supports": supports,
            "rpm": rpm,
            "tpm": tpm,
            "prompt_cache_min_tokens": rec.get("prompt_cache_min_tokens"),
            "search_context_cost_per_query": rec.get("search_context_cost_per_query"),
            "vector_store_cost_per_gb_per_day": rec.get("vector_store_cost_per_gb_per_day"),
            "code_interpreter_cost_per_session": rec.get("code_interpreter_cost_per_session"),
            "computer_use_input_cost_per_1k": rec.get("computer_use_input_cost_per_1k_tokens"),
            "computer_use_output_cost_per_1k": rec.get("computer_use_output_cost_per_1k_tokens"),
            "file_search_cost_per_1k_calls": rec.get("file_search_cost_per_1k_calls"),
            "file_search_cost_per_gb_per_day": rec.get("file_search_cost_per_gb_per_day"),
            "cache_creation_input": cache_creation,
            "input_audio_token_cost": rec.get("input_cost_per_audio_token"),
            "output_audio_token_cost": rec.get("output_cost_per_audio_token"),
            "input_video_per_second": rec.get("input_cost_per_video_per_second"),
            "output_video_per_second": rec.get("output_cost_per_video_per_second"),
            "input_image_cost": rec.get("input_cost_per_image"),
            "output_image_cost": rec.get("output_cost_per_image"),
            "ocr_cost_per_page": rec.get("ocr_cost_per_page"),
            "annotation_cost_per_page": rec.get("annotation_cost_per_page"),
            "tiered_pricing": rec.get("tiered_pricing"),
            "supported_modalities": rec.get("supported_modalities"),
            "supported_output_modalities": rec.get("supported_output_modalities"),
            "supported_endpoints": rec.get("supported_endpoints"),
        }

        offers.append(OfferSnapshot(
            provider_id=rec.get("litellm_provider", model_id.split("/")[0] if "/" in model_id else "litellm"),
            model_id=model_id,
            provider_model_slug=model_id,
            offer_kind="metered_api" if not free else "free_tier",
            input_per_m=(input_cost * 1_000_000) if input_cost is not None else None,
            output_per_m=(output_cost * 1_000_000) if output_cost is not None else None,
            cache_read_per_m=(cache_read * 1_000_000) if cache_read is not None else None,
            free=free,
            requests_day=None,
            tokens_day=None,
            context_tokens=max_input,
            metadata=metadata,
        ))

    return offers
