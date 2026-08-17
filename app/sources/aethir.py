"""app/sources/aethir.py — Aethir GPU Cloud adapter.

Aethir offers compute grants for GPU-intensive AI workloads.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "aethir"
CADENCE_MINUTES = 480
URLS = [
    "https://aethir.com/blog-posts/aethir-the-developers-gpu-cloud",
    "https://aethir.com/pricing",
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

    if re.search(r'(?i)(?:compute\s*grant|free\s*gpu|developer\s*grant|gpu\s*credit)', text):
        offers.append(OfferSnapshot(
            provider_id="aethir", model_id="aethir/compute-grant",
            provider_model_slug="compute", offer_kind="compute_grants", free=True,
            metadata={"source_url": observation.url,
                       "deal_type": "compute_grants",
                       "openai_compatible": False, "difficulty": 3,
                       "requires_application": True,
                       "note": "Apply for GPU compute grants for AI projects"},
        ))

    if re.search(r'(?i)(?:free|trial|试用)', text):
        offers.append(OfferSnapshot(
            provider_id="aethir", model_id="aethir/free-trial",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_trial"},
        ))

    return offers
