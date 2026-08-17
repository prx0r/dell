"""app/sources/upstage.py — Upstage adapter.

Upstage offers $10 signup credit for Solar LLM API.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "upstage"
CADENCE_MINUTES = 480
URLS = [
    "https://www.upstage.ai/pricing/api",
    "https://docs.upstage.ai",
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

    models = re.findall(r'solar[\w.\-]*', text, re.IGNORECASE)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="upstage",
            model_id=f"upstage/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    credit_match = re.search(r'\$(\d+)\s*(?:signup|credit|bonus|free)', text, re.IGNORECASE)
    if credit_match:
        val = int(credit_match.group(1))
        offers.append(OfferSnapshot(
            provider_id="upstage", model_id="upstage/signup-credit",
            provider_model_slug="signup", offer_kind="signup_credits",
            free=True, credits_included=val,
            metadata={"source_url": observation.url, "type": "signup_bonus",
                       "deal_type": "credits", "difficulty": 1},
        ))

    if re.search(r'(?i)(?:free|trial|\$0)', text):
        offers.append(OfferSnapshot(
            provider_id="upstage", model_id="upstage/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    return offers
