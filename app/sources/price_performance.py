"""app/sources/price_performance.py — llm-price-performance-dataset adapter.

Provides model specs, pricing, intelligence scores, and provider info.
"""
from __future__ import annotations

import json
from pathlib import Path
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "price-performance"
CADENCE_MINUTES = 1440
DATA_FILE = Path(__file__).resolve().parents[3] / "llm-price-performance-dataset" / "ai-models.json"


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
    for model in data:
        name = model.get("name", "")
        slug = model.get("slug", "")
        developer = model.get("developer", "")
        input_price = float(model.get("input_price", 0) or 0)
        output_price = float(model.get("output_price", 0) or 0)
        context = model.get("context_window", "")
        max_output = model.get("max_output", "")
        parameters = model.get("parameters", "")
        license_type = model.get("license", "")
        open_weights = model.get("open_weights", "no")
        release_date = model.get("release_date", "")
        api_providers = model.get("api_providers", "")
        intelligence = model.get("intelligence", "")
        modality = model.get("modality", "")

        # Parse context window
        ctx_tokens = None
        if context:
            ctx_str = str(context).upper().replace(",", "")
            if "M" in ctx_str:
                try: ctx_tokens = int(float(ctx_str.replace("M", "")) * 1_000_000)
                except: pass
            elif "K" in ctx_str:
                try: ctx_tokens = int(float(ctx_str.replace("K", "")) * 1000)
                except: pass

        offers.append(OfferSnapshot(
            provider_id=developer,
            model_id=slug or name,
            provider_model_slug=f"{developer}/{slug or name}",
            offer_kind="metered_api" if input_price > 0 else "free_tier",
            input_per_m=input_price * 1_000_000 if input_price else None,
            output_per_m=output_price * 1_000_000 if output_price else None,
            free=input_price == 0 and output_price == 0,
            context_tokens=ctx_tokens,
            metadata={
                "source": "llm-price-performance",
                "name": name,
                "modality": modality,
                "parameters": parameters,
                "license": license_type,
                "open_weights": open_weights,
                "release_date": release_date,
                "api_providers": api_providers,
                "intelligence": intelligence,
            },
        ))

    return offers
