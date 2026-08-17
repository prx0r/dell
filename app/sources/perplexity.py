"""app/sources/perplexity.py — Perplexity AI adapter.

Fetches Perplexity API pricing and documentation.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "perplexity"
CADENCE_MINUTES = 480
URLS = [
    "https://docs.perplexity.ai",
    "https://docs.perplexity.ai/api-reference/quickstart",
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

    models = re.findall(r'(?:sonar|pplx)[\w.-]*', text, re.IGNORECASE)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="perplexity",
            model_id=f"perplexity/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    free_patterns = re.findall(r'(?i)(?:free|no[\s\-]cost|\$0)', text)
    credit_patterns = re.findall(r'(\d[\d,]*)\s*(?:credits?|free\s*tokens?)', text, re.IGNORECASE)

    if free_patterns:
        offers.append(OfferSnapshot(
            provider_id="perplexity", model_id="perplexity/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deals": "free_tier"},
        ))

    for amt in credit_patterns:
        val = int(amt.replace(",", ""))
        if val >= 100:
            offers.append(OfferSnapshot(
                provider_id="perplexity", model_id="perplexity/credits",
                provider_model_slug="credits", offer_kind="signup_credits",
                free=True, credits_included=val,
                metadata={"source_url": observation.url, "type": "signup_bonus"},
            ))

    return offers
