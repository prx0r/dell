"""app/sources/typhoon.py — OpenTyphoon adapter (Thai language models)."""
from __future__ import annotations

import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "opentyphoon"
CADENCE_MINUTES = 480
URLS = [
    "https://opentyphoon.ai",
    "https://opentyphoon.ai/pricing",
]

# Valid model patterns - must look like actual model names, not images/files
MODEL_PATTERN = re.compile(r'(?:typhoon|opentyphoon)[\w.\-]*(?:\d+b?(?:-\w+)*)', re.IGNORECASE)
# Exclude image/file extensions
EXCLUDE = re.compile(r'\.(?:jpg|jpeg|png|gif|svg|webp|pdf|mp4|mp3|wav|zip|tar)', re.IGNORECASE)


def fetch() -> list[Observation]:
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0",
                "Accept": "text/html,application/json",
                "Accept-Language": "th,th;q=0.9,en;q=0.8",
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

    # Only create free tier if we find explicit pricing mention
    if re.search(r'(?i)(?:free\s+tier|free\s+api|gratis|\$0|ฟรี\s+ใช้)', text):
        offers.append(OfferSnapshot(
            provider_id="opentyphoon", model_id="opentyphoon/free-api",
            provider_model_slug="free", offer_kind="free_tier", free=True,
            metadata={"source_url": observation.url, "openai_compatible": True,
                       "region": "th", "focus": "thai_language"}))

    # Extract model names (only actual model names, not images/files)
    for match in MODEL_PATTERN.finditer(text):
        model = match.group()
        # Skip if it looks like a file extension
        if EXCLUDE.search(model):
            continue
        # Skip duplicates
        if any(o.model_id == f"opentyphoon/{model.lower()}" for o in offers):
            continue
        offers.append(OfferSnapshot(
            provider_id="opentyphoon",
            model_id=f"opentyphoon/{model.lower()}",
            provider_model_slug=model,
            offer_kind="metered_api",
            metadata={"source_url": observation.url, "openai_compatible": True,
                       "focus": "thai_language"}))

    return offers
