"""app/sources/nous.py — Nous Portal adapter.

Fetches Nous Portal model catalog and blog for pricing/deals.
"""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "nous-portal"
CADENCE_MINUTES = 120

URLS = [
    "https://portal.nousresearch.com",
    "https://nousresearch.com/blog",
]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0 (https://github.com/prx0r/garglecum)",
                "Accept": "text/html,application/json",
            })
            resp = urllib.request.urlopen(req, timeout=30)
            text = resp.read().decode("utf-8", errors="replace")
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type="provider_page",
                url=url,
                fetched_at=now_iso(),
                status=resp.status,
                text=text,
                sha256=sha256(text),
                etag=resp.headers.get("ETag"),
            ))
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type="provider_page",
                url=url,
                fetched_at=now_iso(),
                status=None,
                text=f"FETCH_ERROR: {e}",
                sha256=sha256(str(e)),
            ))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []

    text = observation.text
    offers = []

    # Look for Nous models
    nous_models = re.findall(r'(?:Nous|nous)[\s\-_]?(Hermes|Llama|Deep|Phi|Mistral|Qwen|Caprice|Dolphi)[\w.\-]*', text)
    for model in set(nous_models):
        full = f"nous-portal/{model.lower()}"
        offers.append(OfferSnapshot(
            provider_id="nous-portal",
            model_id=full,
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url},
        ))

    # Look for pricing signals
    free_patterns = re.findall(r'(?i)(free|no[\s\-]cost|complimentary|trial)', text)
    promo_patterns = re.findall(r'(?i)(\d+)%\s*off|discount|promo(?:tion)?|launch\s*pric', text)

    if free_patterns or promo_patterns:
        for offer in offers:
            if free_patterns:
                offer.free = True
                offer.offer_kind = "temporary_free"
            if promo_patterns:
                offer.metadata["promo_signals"] = promo_patterns

    return offers
