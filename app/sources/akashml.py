"""app/sources/akashml.py — AkashML adapter ($100 signup credits)."""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "akashml"
CADENCE_MINUTES = 1440
URL = "https://akash.network/blog/akashml-managed-ai-inference-on-the-decentralized-supercloud"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode("utf-8", errors="replace")
        return [Observation(source_id=SOURCE_ID, source_type="blog", url=URL,
                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="blog", url=URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []
    # Look for $100 credit
    credit_match = re.search(r'\$(\d+)\s*(?:inference\s*)?credits?', text, re.IGNORECASE)
    if credit_match:
        amount = float(credit_match.group(1))
        offers.append(OfferSnapshot(
            provider_id="akashml", model_id="akashml/signup-credit",
            provider_model_slug="signup-credit", offer_kind="signup_credit",
            credits_included=amount,
            metadata={"source_url": URL, "credit_type": "signup", "automation_allowed": True}))
    return offers
