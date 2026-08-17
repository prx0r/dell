"""app/sources/moonshot.py — Moonshot (Kimi) adapter.

Moonshot offers Kimi API with various pricing tiers.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "moonshot"
CADENCE_MINUTES = 480
URLS = [
    "https://platform.moonshot.cn",
    "https://platform.moonshot.cn/pricing",
]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0",
                "Accept": "text/html,application/json",
                "Accept-Language": "zh-CN,zh;q=0.9",
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

    models = re.findall(r'(?:moonshot|kimi|moon)[\w.\-]*', text, re.IGNORECASE)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="moonshot",
            model_id=f"moonshot/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    if re.search(r'(?i)(?:free|免费|\$0|试用)', text):
        offers.append(OfferSnapshot(
            provider_id="moonshot", model_id="moonshot/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier",
                       "openai_compatible": True, "difficulty": 1},
        ))

    credit_match = re.search(r'(\d[\d,]*)\s*(?:tokens?|credits?)', text, re.IGNORECASE)
    if credit_match:
        val = int(credit_match.group(1).replace(",", ""))
        if val >= 1000:
            offers.append(OfferSnapshot(
                provider_id="moonshot", model_id="moonshot/credits",
                provider_model_slug="credits", offer_kind="signup_credits",
                free=True, credits_included=val,
                metadata={"source_url": observation.url, "type": "signup_bonus"},
            ))

    return offers
