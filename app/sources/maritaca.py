"""app/sources/maritaca.py — Maritaca AI adapter.

Maritaca offers overnight/batch discounts on their LLM API.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "maritaca"
CADENCE_MINUTES = 480
URLS = [
    "https://www.maritaca.ai/planos",
    "https://www.maritaca.ai/pricing",
]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0",
                "Accept": "text/html,application/json",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
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

    if re.search(r'(?i)(?:overnight|batch|desconto|discount)', text):
        discount_match = re.search(r'(\d+)%\s*(?:off|desconto|discount)', text, re.IGNORECASE)
        discount_val = int(discount_match.group(1)) if discount_match else None

        offers.append(OfferSnapshot(
            provider_id="maritaca", model_id="maritaca/batch-discount",
            provider_model_slug="batch", offer_kind="batch_discount", free=False,
            usage_multiplier=0.5 if discount_val and discount_val >= 50 else None,
            metadata={"source_url": observation.url, "deal_type": "overnight_discount",
                       "discount_percent": discount_val,
                       "openai_compatible": True, "difficulty": 1,
                       "region": "br"},
        ))

    if re.search(r'(?i)(?:free|gratuito|\$0)', text):
        offers.append(OfferSnapshot(
            provider_id="maritaca", model_id="maritaca/free-tier",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_tier",
                       "openai_compatible": True, "difficulty": 1},
        ))

    models = re.findall(r'(?:Maritaca|maritaca|Mari)[\w.\-]*', text)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="maritaca",
            model_id=f"maritaca/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    return offers
