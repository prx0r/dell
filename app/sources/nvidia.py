"""app/sources/nvidia.py — NVIDIA NIM adapter.

NVIDIA offers free developer endpoints for NIM microservices.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "nvidia-nim"
CADENCE_MINUTES = 480
URLS = [
    "https://developer.nvidia.com/nim",
    "https://build.nvidia.com",
]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0",
                "Accept": "text/html,application/json",
            })
            resp = urllib.request.urlopen(req, timeout=15)
            text = resp.read().decode("utf-8", errors="replace")
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="provider_page", url=url,
                fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text),
            ))
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="provider_page", url=url,
                fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}",
                sha256=sha256(str(e)),
            ))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []

    if re.search(r'(?i)(?:free|developer|free\s*tier|试用)', text):
        offers.append(OfferSnapshot(
            provider_id="nvidia-nim", model_id="nvidia-nim/free-endpoints",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_dev_endpoints",
                       "openai_compatible": True, "difficulty": 2,
                       "rate_limit": "1000 requests/day (typical)",
                       "note": "Requires NVIDIA developer account"},
        ))

    models = re.findall(r'(?:nvidia|nim|meta-llama|mistral|google)[\w.\-/]*', text, re.IGNORECASE)
    for model in set(models):
        if len(model) > 3:
            offers.append(OfferSnapshot(
                provider_id="nvidia-nim",
                model_id=f"nvidia-nim/{model.lower().replace('/', '-')}",
                provider_model_slug=model,
                offer_kind="metered_api",
                metadata={"source_url": observation.url, "openai_compatible": True},
            ))

    return offers
