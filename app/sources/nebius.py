"""app/sources/nebius.py — Nebius AI adapter.

Nebius offers Token Factory credits for their cloud GPU platform.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "nebius"
CADENCE_MINUTES = 480
URLS = [
    "https://nebius.com/pricing",
    "https://nebius.com",
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

    if re.search(r'(?i)(?:token\s*factory|free\s*credit|signup\s*credit|\$100)', text):
        credit_match = re.search(r'\$(\d[\d,]*)', text, re.IGNORECASE)
        credit_val = int(credit_match.group(1).replace(",", "")) if credit_match else None

        offers.append(OfferSnapshot(
            provider_id="nebius", model_id="nebius/token-factory",
            provider_model_slug="token-factory", offer_kind="signup_credits", free=True,
            credits_included=credit_val,
            metadata={"source_url": observation.url,
                       "deal_type": "token_factory_credits",
                       "openai_compatible": True, "difficulty": 1,
                       "note": "Token Factory credits for new users"},
        ))

    if re.search(r'(?i)(?:free|trial|\$0)', text):
        offers.append(OfferSnapshot(
            provider_id="nebius", model_id="nebius/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier",
                       "openai_compatible": True, "difficulty": 1},
        ))

    return offers
