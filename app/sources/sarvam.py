"""app/sources/sarvam.py — Sarvam AI adapter.

Sarvam offers free developer credits for their Indian language LLM platform.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "sarvam"
CADENCE_MINUTES = 480
URLS = [
    "https://docs.sarvam.ai",
    "https://sarvam.ai/pricing",
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

    if re.search(r'(?i)(?:free|dev\s*credit|developer|免费)', text):
        credit_match = re.search(r'(\d[\d,]*)\s*(?:free\s*credit|dev\s*credit|tokens?)', text, re.IGNORECASE)
        credit_val = int(credit_match.group(1).replace(",", "")) if credit_match else None

        offers.append(OfferSnapshot(
            provider_id="sarvam", model_id="sarvam/free-credits",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            credits_included=credit_val,
            metadata={"source_url": observation.url, "deal_type": "free_dev_credits",
                       "openai_compatible": True, "difficulty": 1,
                       "region": "in", "focus": "indian_languages"},
        ))

    models = re.findall(r'(?:sarvam|saaras)[\w.\-]*', text, re.IGNORECASE)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="sarvam",
            model_id=f"sarvam/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    return offers
