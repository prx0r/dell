"""app/sources/free_llm_apis.py — awesome-free-llm-apis adapter.

Parses the curated data.json from the awesome-free-llm-apis repo.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "awesome-free-llm-apis"
CADENCE_MINUTES = 1440  # 24h
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


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []

    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    for provider in data if isinstance(data, list) else data.get("providers", []):
        provider_name = provider.get("name", provider.get("provider", "unknown"))
        for model in provider.get("models", []):
            model_name = model.get("name", model.get("model", ""))
            context = model.get("context_length") or model.get("context")
            rpm = model.get("rpm") or model.get("requests_per_minute")
            tpd = model.get("tpd") or model.get("tokens_per_day")

            offers.append(OfferSnapshot(
                provider_id=provider_name,
                model_id=model_name,
                provider_model_slug=f"{provider_name}/{model_name}",
                offer_kind="free_tier",
                free=True,
                requests_day=rpm * 60 * 24 if rpm else None,
                tokens_day=tpd,
                context_tokens=context,
                metadata={"source": "awesome-free-llm-apis", "base_url": provider.get("base_url", "")},
            ))

    return offers
