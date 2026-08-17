"""app/sources/aion.py — Aion Labs adapter.

Aion Labs offers daily free credits for their AI platform.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "aion"
CADENCE_MINUTES = 480
URL = "https://www.aionlabs.ai/pricing"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(URL, headers={
            "User-Agent": "deal-radar/2.0",
            "Accept": "text/html,application/json",
        })
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode("utf-8", errors="replace")
        return [Observation(
            source_id=SOURCE_ID, source_type="provider_page", url=URL,
            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text),
        )]
    except Exception as e:
        return [Observation(
            source_id=SOURCE_ID, source_type="provider_page", url=URL,
            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}",
            sha256=sha256(str(e)),
        )]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []

    if re.search(r'(?i)(?:free|daily|daily\s*credit|免费)', text):
        credit_match = re.search(r'(\d[\d,]*)\s*(?:daily\s*credit|free\s*credit|每日)', text, re.IGNORECASE)
        credit_val = int(credit_match.group(1).replace(",", "")) if credit_match else None

        offers.append(OfferSnapshot(
            provider_id="aion", model_id="aion/daily-free",
            provider_model_slug="daily-free", offer_kind="free_tier", free=True,
            credits_included=credit_val,
            metadata={"source_url": URL, "deal_type": "daily_credits",
                       "openai_compatible": False, "difficulty": 1,
                       "region": "global"},
        ))

    if re.search(r'(?i)(?:compute|gpu|grant)', text):
        offers.append(OfferSnapshot(
            provider_id="aion", model_id="aion/compute-grant",
            provider_model_slug="compute", offer_kind="signup_credits", free=True,
            metadata={"source_url": URL, "deal_type": "compute_grants"},
        ))

    return offers
