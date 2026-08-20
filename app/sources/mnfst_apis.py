"""app/sources/mnfst_apis.py — Consume mnfst/awesome-free-llm-apis/data.json as baseline data.

Reads the curated free-tier list and produces OfferSnapshot records.
This is the baseline: every free tier that's verified and maintained by the community.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "mnfst-awesome-free-llm-apis"
CADENCE_MINUTES = 1440  # 24 hours — upstream updates daily

DATA_URL = "https://raw.githubusercontent.com/mnfst/awesome-free-llm-apis/main/data.json"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        text = resp.read().decode("utf-8", errors="replace")
        return [Observation(
            source_id=SOURCE_ID,
            source_type="github_json",
            url=DATA_URL,
            fetched_at=now_iso(),
            status=resp.status,
            text=text,
            sha256=sha256(text)
        )]
    except Exception as e:
        return [Observation(
            source_id=SOURCE_ID,
            source_type="github_json",
            url=DATA_URL,
            fetched_at=now_iso(),
            status=None,
            text=f"FETCH_ERROR: {e}",
            sha256=sha256(str(e))
        )]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []

    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []

    offers = []
    providers = data.get("providers", [])

    for provider in providers:
        name = provider.get("name", "unknown")
        category = provider.get("category", "unknown")
        country = provider.get("country", "")
        flag = provider.get("flag", "")
        base_url = provider.get("baseUrl", "")
        description = provider.get("description", "")
        url = provider.get("url", "")

        # Parse rate limits from description
        is_free = "free" in description.lower() or "permanent" in description.lower()
        requires_card = "credit card" in description.lower() and "no credit card" not in description.lower()
        requires_kyc = "verification" in description.lower() or "real-name" in description.lower()

        for model in provider.get("models", []):
            model_id = model.get("id") or model.get("name", "unknown")
            context_str = model.get("context", "")
            rate_limit = model.get("rateLimit", "")
            modality = model.get("modality", "")

            # Parse context tokens
            context_tokens = None
            if context_str and context_str != "—":
                ctx_clean = context_str.replace(",", "").replace("K", "000").replace("M", "000000")
                try:
                    context_tokens = int(float(ctx_clean))
                except (ValueError, TypeError):
                    pass

            # Parse rate limits
            requests_day = None
            requests_month = None
            if "RPD" in rate_limit:
                import re
                rpd_match = re.search(r'(\d[\d,]*)\s*RPD', rate_limit)
                if rpd_match:
                    requests_day = int(rpd_match.group(1).replace(",", ""))
            if "month" in rate_limit.lower():
                import re
                rpm_match = re.search(r'(\d[\d,]*)\s*(?:calls?|req)', rate_limit)
                if rpm_match:
                    requests_month = int(rpm_match.group(1).replace(",", ""))

            offers.append(OfferSnapshot(
                provider_id=name.lower().replace(" ", "-").replace("/", "-"),
                model_id=f"{name.lower().replace(' ', '-')}/{model_id}",
                provider_model_slug=model_id,
                offer_kind="free_tier",
                free=is_free,
                requests_day=requests_day,
                requests_month=requests_month,
                context_tokens=context_tokens,
                metadata={
                    "source_url": url,
                    "data_url": DATA_URL,
                    "category": category,
                    "country": country,
                    "flag": flag,
                    "base_url": base_url,
                    "description": description,
                    "rate_limit_raw": rate_limit,
                    "modality": modality,
                    "requires_credit_card": requires_card,
                    "requires_kyc": requires_kyc,
                    "extracted_from": "mnfst_data_json"
                }
            ))

    return offers
