"""app/sources/siliconflow.py — SiliconFlow adapter.

SiliconFlow offers free quotas for several models and credits for new users.
"""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "siliconflow"
CADENCE_MINUTES = 480
URLS = [
    "https://docs.siliconflow.cn/cn/release-notes/overview",
    "https://siliconflow.cn/pricing",
]


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0",
                "Accept": "text/html,application/json",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
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

    if re.search(r'(?i)(?:free|免费|\$0|赠金|额度)', text):
        credit_match = re.search(r'(\d[\d,]*)\s*(?:tokens?|credits?|免费额度)', text, re.IGNORECASE)
        credits_val = int(credit_match.group(1).replace(",", "")) if credit_match else None

        offers.append(OfferSnapshot(
            provider_id="siliconflow", model_id="siliconflow/free-quota",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            credits_included=credits_val,
            metadata={"source_url": observation.url, "deal_type": "free_quota",
                       "openai_compatible": True, "region": "cn",
                       "difficulty": 1, "new_user_bonus": True},
        ))

    models = re.findall(r'(?:Qwen|DeepSeek|Llama|ChatGLM|InternLM|Yi)[\w.\-]*', text)
    for model in set(models):
        offers.append(OfferSnapshot(
            provider_id="siliconflow",
            model_id=f"siliconflow/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True},
        ))

    return offers
