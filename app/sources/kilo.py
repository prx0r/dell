"""app/sources/kilo.py — Kilo AI adapter.

Kilo AI offers Auto Free routing across multiple providers.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "kilo"
CADENCE_MINUTES = 480
URLS = [
    "https://kilo.ai/pricing",
    "https://kilo.ai",
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

    if re.search(r'(?i)(?:auto\s*free|free\s*routing|free\s*tier)', text):
        offers.append(OfferSnapshot(
            provider_id="kilo", model_id="kilo/auto-free",
            provider_model_slug="auto-free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url,
                       "deal_type": "auto_free_routing",
                       "openai_compatible": True, "difficulty": 1,
                       "note": "Routes to cheapest/free providers automatically"},
        ))

    if re.search(r'(?i)(?:free|gratis|\$0)', text):
        offers.append(OfferSnapshot(
            provider_id="kilo", model_id="kilo/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier",
                       "openai_compatible": True, "difficulty": 1},
        ))

    credit_match = re.search(r'(\d[\d,]*)\s*(?:credits?|free)', text, re.IGNORECASE)
    if credit_match:
        val = int(credit_match.group(1).replace(",", ""))
        if val >= 100:
            offers.append(OfferSnapshot(
                provider_id="kilo", model_id="kilo/credits",
                provider_model_slug="credits", offer_kind="signup_credits",
                free=True, credits_included=val,
                metadata={"source_url": observation.url, "type": "signup_bonus"},
            ))

    return offers
