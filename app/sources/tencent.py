"""app/sources/tencent.py — Tencent Cloud TokenHub adapter.

Tencent offers free trial quotas for various models on their cloud platform.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "tencent"
CADENCE_MINUTES = 1440
URLS = [
    "https://cloud.tencent.com/document/product/1823/130053",
    "https://cloud.tencent.com/document/product/1729",
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

    if re.search(r'(?i)(?:free|免费|试用|trial)', text):
        quota_match = re.search(r'(\d[\d,]*)\s*(?:万|万?)\s*(?:tokens?|次)', text)
        quota_val = int(quota_match.group(1).replace(",", "")) if quota_match else None

        offers.append(OfferSnapshot(
            provider_id="tencent", model_id="tencent/free-trial",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            tokens_day=quota_val,
            metadata={"source_url": observation.url, "deal_type": "free_trial",
                       "openai_compatible": True, "region": "cn",
                       "difficulty": 2, "note": "Requires Tencent Cloud account"},
        ))

    models = re.findall(r'(?:Hunyuan|hunyuan|混元)[\w.\-]*', text)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="tencent",
            model_id=f"tencent/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    return offers
