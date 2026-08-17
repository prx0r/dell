"""app/sources/sakura.py — Sakura AI Engine adapter (3000 req/month free, Japan)."""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "sakura-ai"
CADENCE_MINUTES = 1440
URLS = ["https://cloud.sakura.ad.jp/", "https://www.sakura.ad.jp/corporate/information/announcements/2026/07/14/1968225322/"]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deal-radar/2.0", "Accept-Language": "ja,en;q=0.8"})
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
    if re.search(r'無料|free|3.?000', text):
        offers.append(OfferSnapshot(
            provider_id="sakura-ai", model_id="sakura-ai/free-tier",
            provider_model_slug="free-tier", offer_kind="renewable_free_quota", free=True,
            requests_day=100,  # 3000/month ≈ 100/day
            metadata={"source_url": observation.url, "quota_monthly": 3000,
                      "reset": "monthly", "phone_verification": "required",
                      "international_eligibility": "unverified", "openai_compat": True,
                      "auto_charge": False}))
    return offers
