"""app/sources/minimax.py — MiniMax adapter.

MiniMax offers token plans with various tiers and pricing.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "minimax"
CADENCE_MINUTES = 480
URLS = [
    "https://platform.minimax.io/subscribe/token-plan",
    "https://platform.minimax.io/pricing",
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

    models = re.findall(r'(?:abab|MiniMax|minimax)[\w.\-]*', text, re.IGNORECASE)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="minimax",
            model_id=f"minimax/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    plan_matches = re.findall(r'(\d[\d,]*)\s*(?:tokens?|万tokens?)', text, re.IGNORECASE)
    for amt in plan_matches:
        val = int(amt.replace(",", ""))
        if val >= 10000:
            offers.append(OfferSnapshot(
                provider_id="minimax", model_id=f"minimax/plan-{val}",
                provider_model_slug=f"plan-{val}", offer_kind="subscription_plan",
                tokens_day=val,
                metadata={"source_url": observation.url, "type": "token_plan"},
            ))

    if re.search(r'(?i)(?:free|免费|\$0|试用|trial)', text):
        offers.append(OfferSnapshot(
            provider_id="minimax", model_id="minimax/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier",
                       "openai_compatible": True, "difficulty": 1},
        ))

    return offers
