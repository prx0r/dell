"""app/sources/infini.py — Infini-AI adapter.

Infini-AI offers free embeddings and reranker endpoints.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "infini-ai"
CADENCE_MINUTES = 480
URLS = [
    "https://docs.infini-ai.com",
    "https://infini-ai.com/pricing",
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

    if re.search(r'(?i)(?:embed|rerank|免费|free)', text):
        offers.append(OfferSnapshot(
            provider_id="infini-ai", model_id="infini-ai/embeddings-free",
            provider_model_slug="embeddings", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "deal_type": "free_embeddings",
                       "openai_compatible": True, "difficulty": 1,
                       "endpoints": ["embeddings", "reranker"]},
        ))

    models = re.findall(r'(?:infini|emmental|bge)[\w.\-]*', text, re.IGNORECASE)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="infini-ai",
            model_id=f"infini-ai/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    return offers
