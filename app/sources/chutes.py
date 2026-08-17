"""app/sources/chutes.py — Chutes AI adapter.

Chutes AI offers startup credits up to $10K for developers.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "chutes"
CADENCE_MINUTES = 480
URLS = [
    "https://chutes.ai/pricing",
    "https://chutes.ai",
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

    credit_match = re.search(r'\$(\d[\d,]*[KkMm]?)\s*(?:startup|credit|free|grant)', text, re.IGNORECASE)
    if credit_match:
        raw = credit_match.group(1).replace(",", "")
        multiplier = 1000 if raw.upper().endswith("K") else 1000000 if raw.upper().endswith("M") else 1
        val = float(re.sub(r'[KkMm]', '', raw)) * multiplier
        offers.append(OfferSnapshot(
            provider_id="chutes", model_id="chutes/startup-credit",
            provider_model_slug="startup", offer_kind="signup_credits", free=True,
            credits_included=int(val),
            metadata={"source_url": observation.url, "deal_type": "startup_credits",
                       "max_value": 10000, "openai_compatible": True,
                       "difficulty": 2, "requires_application": True},
        ))

    if re.search(r'(?i)(?:free|gratis|\$0)', text):
        offers.append(OfferSnapshot(
            provider_id="chutes", model_id="chutes/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier",
                       "openai_compatible": True, "difficulty": 1},
        ))

    return offers
