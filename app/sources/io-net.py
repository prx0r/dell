"""app/sources/io-net.py — io.net GPU Cloud adapter.

io.net offers $100 free GPU trial credits.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "io-net"
CADENCE_MINUTES = 480
URLS = [
    "https://io.net",
    "https://io.net/pricing",
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

    credit_match = re.search(r'\$(\d[\d,]*)\s*(?:free|trial|gpu|credit)', text, re.IGNORECASE)
    if credit_match:
        val = int(credit_match.group(1).replace(",", ""))
        offers.append(OfferSnapshot(
            provider_id="io-net", model_id="io-net/free-trial",
            provider_model_slug="free-trial", offer_kind="signup_credits", free=True,
            credits_included=val,
            metadata={"source_url": observation.url,
                       "deal_type": "gpu_trial_credits",
                       "openai_compatible": False, "difficulty": 2,
                       "note": "$100 free GPU trial credits",
                       "gpu_types": ["NVIDIA A100", "H100", "RTX 4090"]},
        ))

    if re.search(r'(?i)(?:free|trial|\$0)', text):
        offers.append(OfferSnapshot(
            provider_id="io-net", model_id="io-net/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier"},
        ))

    return offers
