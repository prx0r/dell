"""app/sources/zai.py — Z.AI adapter (GLM free models + Coding Plan)."""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "zai"
CADENCE_MINUTES = 240
URLS = ["https://docs.z.ai/guides/overview/pricing", "https://docs.z.ai/devpack/overview"]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deal-radar/2.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            text = resp.read().decode("utf-8", errors="replace")
            observations.append(Observation(source_id=SOURCE_ID, source_type="provider_page", url=url,
                                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text)))
        except Exception as e:
            observations.append(Observation(source_id=SOURCE_ID, source_type="provider_page", url=url,
                                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e))))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []
    # Look for GLM free models
    free_models = re.findall(r'(GLM-[\d.]+[\w]*(?:-\w+)*)\s*(?:FREE|Free|\$0)', text)
    for model in free_models:
        offers.append(OfferSnapshot(
            provider_id="zai", model_id=f"zai/{model.lower()}",
            provider_model_slug=model, offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url}))
    # Look for Coding Plan pricing
    coding_match = re.search(r'Coding\s*Plan.*?\$(\d+)', text, re.IGNORECASE)
    if coding_match:
        offers.append(OfferSnapshot(
            provider_id="zai", model_id="zai/coding-plan",
            provider_model_slug="coding-plan", offer_kind="subscription_allowance",
            subscription_usd=float(coding_match.group(1)),
            metadata={"source_url": observation.url, "plan": "coding"}))
    return offers
