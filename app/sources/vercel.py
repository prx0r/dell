"""app/sources/vercel.py — Vercel AI Gateway changelog adapter.

Vercel's changelog explicitly contains launch-pricing windows and expiration dates —
exactly the temporal facts V2 needs.
"""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "vercel-changelog"
CADENCE_MINUTES = 120
URL = "https://vercel.com/changelog/claude-sonnet-5-ai-gateway"

PRICING_KEYWORDS = re.compile(
    r"(free|discount|%[\s]*off|promo|launch[\s]*pric|credits?|bonus|"
    r"[2-9]x[\s]*(?:usage|tokens?|quota)|limited[\s]*time|expires?|"
    r"through|until|off[\s]*peak|price[\s]*cut|\$[\d.]+)", re.IGNORECASE)


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode("utf-8", errors="replace")
        return [Observation(source_id=SOURCE_ID, source_type="changelog", url=URL,
                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="changelog", url=URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    offers = []
    text = observation.text

    # Find pricing-related sections
    for match in PRICING_KEYWORDS.finditer(text):
        context = text[max(0, match.start()-200):match.end()+200]
        keywords = PRICING_KEYWORDS.findall(context)
        if len(keywords) >= 2:
            offers.append(OfferSnapshot(
                provider_id="vercel", model_id=None, provider_model_slug=None,
                offer_kind="community_lead",
                metadata={"source_url": URL, "excerpt": context[:500],
                          "keywords": keywords}))
    return offers
