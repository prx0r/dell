"""app/sources/scaleway.py — Scaleway adapter (1M free tokens, France)."""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "scaleway"
CADENCE_MINUTES = 1440
URL = "https://www.scaleway.com/en/generative-apis/"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode("utf-8", errors="replace")
        return [Observation(source_id=SOURCE_ID, source_type="provider_page", url=URL,
                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="provider_page", url=URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []
    if re.search(r'1[\s,]*000[\s,]*000\s*(?:free\s*)?tokens?', text, re.IGNORECASE):
        offers.append(OfferSnapshot(
            provider_id="scaleway", model_id="scaleway/free-tokens",
            provider_model_slug="generative-apis-free", offer_kind="signup_credit", free=True,
            credits_included=1000000,
            metadata={"source_url": URL, "credit_type": "signup", "tokens": 1000000,
                      "applies_to": "most_expensive_first", "automation_allowed": True}))
    return offers
