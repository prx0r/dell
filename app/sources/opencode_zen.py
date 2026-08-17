"""app/sources/opencode_zen.py — OpenCode Zen adapter (free API models).

Zen lists actual free API endpoints including MiMo, Hy3, DeepSeek, Nemotron.
"""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "opencode-zen"
CADENCE_MINUTES = 240  # 4h
URL = "https://opencode.ai/docs/zen/"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode("utf-8", errors="replace")
        return [Observation(source_id=SOURCE_ID, source_type="provider_page", url=URL,
                            fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="provider_page", url=URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []
    # Look for free model patterns: "Model Name Free" or "$0"
    free_patterns = re.findall(r'([\w./-]+(?:\s+[\w./-]+)*)\s*(?:Free|FREE|\$0)', text)
    for model in free_patterns:
        model = model.strip()
        if len(model) < 3:
            continue
        offers.append(OfferSnapshot(
            provider_id="opencode-zen",
            model_id=f"opencode-zen/{model.lower().replace(' ', '-')}",
            provider_model_slug=model,
            offer_kind="free_tier",
            free=True,
            metadata={"source_url": URL}))
    return offers
