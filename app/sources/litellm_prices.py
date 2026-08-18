"""app/sources/litellm_prices.py — litellm model_prices_and_context_window.json adapter.

Uses the local litellm clone for comprehensive model pricing data.
"""
from __future__ import annotations

import json
from pathlib import Path
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "litellm-prices"
CADENCE_MINUTES = 1440  # 24h
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

        max_input = rec.get("max_input_tokens") or rec.get("max_tokens")
        rpm = rec.get("rpm_limit")
        tpd = rec.get("requests_per_day")

        # Parse cost
        input_cost = rec.get("input_cost_per_token")
        output_cost = rec.get("output_cost_per_token")
        cache_cost = rec.get("cache_read_input_token_cost")

        # Determine if free
        free = (input_cost == 0 or input_cost is None) and (output_cost == 0 or output_cost is None)

        offers.append(OfferSnapshot(
            provider_id=rec.get("litellm_provider", model_id.split("/")[0] if "/" in model_id else "litellm"),
            model_id=model_id,
            provider_model_slug=model_id,
            offer_kind="metered_api" if not free else "free_tier",
            input_per_m=(input_cost * 1_000_000) if input_cost is not None else None,
            output_per_m=(output_cost * 1_000_000) if output_cost is not None else None,
            cache_read_per_m=(cache_cost * 1_000_000) if cache_cost is not None else None,
            free=free,
            requests_day=tpd,
            context_tokens=max_input,
            metadata={"source": "litellm", "mode": rec.get("mode", "chat")},
        ))

    return offers
