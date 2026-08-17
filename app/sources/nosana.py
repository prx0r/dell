"""app/sources/nosana.py — Nosana adapter.

Nosana offers free GPU credits for AI inference workloads on Solana.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "nosana"
CADENCE_MINUTES = 480
URLS = [
    "https://nosana.com",
    "https://nosana.com/pricing",
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

    if re.search(r'(?i)(?:free\s*gpu|gpu\s*credit|free\s*compute)', text):
        credit_match = re.search(r'(\d[\d,]*)\s*(?:free\s*credit|gpu\s*credit)', text, re.IGNORECASE)
        credit_val = int(credit_match.group(1).replace(",", "")) if credit_match else None

        offers.append(OfferSnapshot(
            provider_id="nosana", model_id="nosana/free-gpu",
            provider_model_slug="free-gpu", offer_kind="free_tier", free=True,
            credits_included=credit_val,
            metadata={"source_url": observation.url,
                       "deal_type": "free_gpu_credits",
                       "openai_compatible": False, "difficulty": 2,
                       "blockchain": "solana",
                       "note": "Free GPU credits for inference workloads"},
        ))

    if re.search(r'(?i)(?:free|trial|试用)', text):
        offers.append(OfferSnapshot(
            provider_id="nosana", model_id="nosana/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier"},
        ))

    return offers
