"""app/sources/alibaba.py — Alibaba Bailian adapter (per-model free quotas).

Key discovery: 1M free tokens PER MODEL, independent quotas, 90-day validity.
"""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "alibaba"
CADENCE_MINUTES = 1440  # 24h
URLS = [
    "https://help.aliyun.com/zh/model-studio/new-free-quota",
    "https://help.aliyun.com/zh/model-studio/model-pricing",
]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
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
    # Look for free quota patterns (1M tokens per model)
    quota_match = re.search(r'(\d+)\s*(?:万|万?)\s*(?:tokens?|token)', text)
    if quota_match:
        amount = int(quota_match.group(1))
        if amount >= 100000:  # 100K+ tokens
            offers.append(OfferSnapshot(
                provider_id="alibaba", model_id="alibaba/free-quota",
                provider_model_slug="bailian-free", offer_kind="per_model_free_quota",
                free=True, tokens_day=amount,
                metadata={"source_url": observation.url, "quota_type": "per_model",
                          "validity_days": 90, "region": "cn-beijing"}))
    # Look for specific models
    model_names = re.findall(r'(qwen[\w.-]*)', text, re.IGNORECASE)
    for model in set(model_names):
        offers.append(OfferSnapshot(
            provider_id="alibaba", model_id=f"alibaba/{model.lower()}",
            provider_model_slug=model, offer_kind="per_model_free_quota", free=True,
            metadata={"source_url": observation.url, "note": "independent per-model quota"}))
    return offers
