"""app/sources/ovhcloud.py — OVHcloud adapter ($200 signup credits, virtual model router)."""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "ovhcloud"
CADENCE_MINUTES = 1440
URLS = [
    "https://www.ovhcloud.com/en/public-cloud/ai-machine-learning/ai-deploy-partners/",
    "https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-capabilities",
]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deal-radar/2.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            text = resp.read().decode("utf-8", errors="replace")
            observations.append(Observation(source_id=SOURCE_ID, source_type="provider_page", url=url,
                                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text)))
        except Exception as e:
            observations.append(Observation(source_id=SOURCE_ID, source_type="provider_page", url=url,
                                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e))))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []
    credit_match = re.search(r'\$(\d+)\s*(?:free\s*)?credit', text, re.IGNORECASE)
    if credit_match:
        offers.append(OfferSnapshot(
            provider_id="ovhcloud", model_id="ovhcloud/signup-credit",
            provider_model_slug="signup-credit", offer_kind="signup_credit",
            credits_included=float(credit_match.group(1)),
            metadata={"source_url": observation.url, "openai_compat": True,
                      "virtual_router": True, "automation_allowed": True}))
    return offers
