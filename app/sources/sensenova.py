"""app/sources/sensenova.py — SenseNova adapter ($0 public beta, 1500 calls/model/5h)."""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "sensenova"
CADENCE_MINUTES = 240
URL = "https://www.sensenova.ai/token-plan"


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
    if re.search(r'\$0|free|免费|public\s*beta', text, re.IGNORECASE):
        calls_match = re.search(r'(\d[\d,]*)\s*(?:calls?|API)', text, re.IGNORECASE)
        calls = int(calls_match.group(1).replace(',', '')) if calls_match else 1500
        offers.append(OfferSnapshot(
            provider_id="sensenova", model_id="sensenova/public-beta",
            provider_model_slug="public-beta", offer_kind="free_tier", free=True,
            requests_day=calls * 5,  # per 5h window
            metadata={"source_url": URL, "calls_per_window": calls, "window_hours": 5,
                      "max_api_keys": 20, "automation_allowed": True,
                      "global_access": True}))
    return offers
