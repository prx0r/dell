"""app/sources/free_llm_apis.py — awesome-free-llm-apis adapter.

Extracts full provider/model details: name, country, base URL, context,
max output, modality, rate limits, description, category.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "awesome-free-llm-apis"
CADENCE_MINUTES = 1440
DATA_URL = "https://raw.githubusercontent.com/mnfst/awesome-free-llm-apis/main/data.json"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "dell/2.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        text = resp.read().decode("utf-8")
        return [Observation(source_id=SOURCE_ID, source_type="api_json", url=DATA_URL,
                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="api_json", url=DATA_URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]


def _parse_context(ctx_str: str) -> int | None:
    """Parse context string like '128K', '~4K', '32,768' to integer."""
    if not ctx_str:
        return None
    ctx_str = str(ctx_str).strip().upper()
    # Remove common prefixes
    ctx_str = ctx_str.lstrip("~≈<>")
    # Remove commas
    ctx_str = ctx_str.replace(",", "")
    if ctx_str.endswith("K"):
        try:
            return int(float(ctx_str[:-1]) * 1000)
        except ValueError:
            return None
    if ctx_str.endswith("M"):
        try:
            return int(float(ctx_str[:-1]) * 1_000_000)
        except ValueError:
            return None
    try:
        return int(ctx_str)
    except ValueError:
        return None


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []

    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    providers = data.get("providers", [])

    for provider in providers:
        provider_name = provider.get("name", "unknown")
        provider_category = provider.get("category", "")
        provider_country = provider.get("country", "")
        provider_url = provider.get("url", "")
        provider_base_url = provider.get("baseUrl", "")
        provider_description = provider.get("description", "")

        for model in provider.get("models", []):
            model_id = model.get("id", "")
            model_name = model.get("name", model_id)
            context = _parse_context(model.get("context", ""))
            max_output = _parse_context(model.get("maxOutput", ""))
            modality = model.get("modality", "")
            rate_limit = model.get("rateLimit", "")

            # Parse rate limits
            rpm = None
            tpd = None
            if rate_limit:
                rl = str(rate_limit).lower()
                if "rpm" in rl:
                    try:
                        rpm = int("".join(c for c in rl.split("rpm")[0] if c.isdigit()))
                    except ValueError:
                        pass
                if "tpd" in rl or "tokens/day" in rl:
                    try:
                        tpd = int("".join(c for c in rl.split("tpd")[0] if c.isdigit()))
                    except ValueError:
                        pass

            offers.append(OfferSnapshot(
                provider_id=provider_name,
                model_id=model_id,
                provider_model_slug=f"{provider_name}/{model_id}",
                offer_kind="free_tier",
                free=True,
                requests_day=rpm * 60 * 24 if rpm else None,
                tokens_day=tpd,
                context_tokens=context,
                metadata={
                    "source": "awesome-free-llm-apis",
                    "category": provider_category,
                    "country": provider_country,
                    "url": provider_url,
                    "base_url": provider_base_url,
                    "description": provider_description,
                    "modality": modality,
                    "rate_limit": rate_limit,
                    "max_output": max_output,
                },
            ))

    return offers
