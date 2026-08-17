"""app/sources/opencode.py — OpenCode Go adapter.

Extracts model-specific deals from the Go landing page using data attributes.
"""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "opencode-go"
CADENCE_MINUTES = 120
URLS = [
    "https://dev.opencode.ai/go",
    "https://opencode.ai/data",
    "https://opencode.ai",
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
                fetched_at=now_iso(), status=resp.status, text=text,
                sha256=sha256(text), etag=resp.headers.get("ETag"),
                last_modified=resp.headers.get("Last-Modified"),
            ))
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="provider_page", url=url,
                fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}",
                sha256=sha256(str(e))))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract offers from OpenCode Go page.

    The page uses data attributes:
    - data-model="MODEL_NAME" — the model
    - data-bonus>Nx usage — multiplier (e.g. "2x usage")
    - data-model="X" ... NNN requests — request count
    - data-kind="go" — Go plan models
    - data-kind="promo" — promotional models
    """
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []

    # Strategy 1: Find data-model + data-bonus pairs (model-specific multipliers)
    # Pattern: data-model="MODEL" ... data-bonus>Nx usage
    model_mults = re.findall(
        r'data-model="([^"]+)"[^>]*>.*?data-bonus>(\d+)x',
        text, re.DOTALL
    )
    for model, mult in model_mults:
        if len(model) < 3:
            continue
        offers.append(OfferSnapshot(
            provider_id="opencode-go",
            model_id="opencode-go/%s" % model.lower(),
            provider_model_slug=model,
            offer_kind="usage_multiplier",
            usage_multiplier=float(mult),
            metadata={
                "source_url": observation.url,
                "extracted_from": "data_attribute",
                "multiplier": float(mult),
                "evidence": "data-model=%s data-bonus>%sx usage" % (model, mult),
            },
        ))

    # Strategy 2: Find data-model + request count pairs
    model_requests = re.findall(
        r'data-model="([^"]+)"[^>]*>.*?data-value>([\d,]+)<',
        text, re.DOTALL
    )
    existing_models = {o.model_id for o in offers}
    
    # Calculate baseline (median request count) for multiplier detection
    counts = [int(c.replace(",", "")) for _, c in model_requests]
    baseline = sorted(counts)[len(counts)//2] if counts else 1000
    
    for model, count in model_requests:
        if len(model) < 3:
            continue
        mid = "opencode-go/%s" % model.lower()
        count_int = int(count.replace(",", ""))
        
        # Detect if this model has significantly more requests than baseline
        multiplier = round(count_int / baseline, 1) if baseline > 0 else 1.0
        
        if mid in existing_models:
            for o in offers:
                if o.model_id == mid:
                    o.metadata["requests_per_5h"] = count_int
                    if multiplier > 1.5:
                        o.offer_kind = "capacity_multiplier"
                        o.metadata["capacity_multiplier"] = multiplier
                        o.metadata["evidence"] = "%s req/5h vs baseline %s req/5h = %.1fx capacity" % (count, baseline, multiplier)
            continue
        
        offer_kind = "capacity_multiplier" if multiplier > 1.5 else "metered_api"
        offers.append(OfferSnapshot(
            provider_id="opencode-go",
            model_id=mid,
            provider_model_slug=model,
            offer_kind=offer_kind,
            usage_multiplier=multiplier if multiplier > 1.5 else None,
            metadata={
                "source_url": observation.url,
                "extracted_from": "data_attribute",
                "requests_per_5h": count_int,
                "capacity_multiplier": multiplier,
                "baseline_requests_per_5h": baseline,
                "evidence": "%s req/5h vs baseline %s req/5h = %.1fx capacity" % (count, baseline, multiplier),
            },
        ))

    # Strategy 3: Find data-model with kind="go" or kind="promo"
    go_models = re.findall(r'data-kind="(?:go|promo)"[^>]*data-model="([^"]+)"', text)
    promo_models = re.findall(r'data-kind="promo"[^>]*data-model="([^"]+)"', text)
    existing_models = {o.model_id for o in offers}
    for model in go_models + promo_models:
        if len(model) < 3:
            continue
        mid = "opencode-go/%s" % model.lower()
        if mid not in existing_models:
            offers.append(OfferSnapshot(
                provider_id="opencode-go",
                model_id=mid,
                provider_model_slug=model,
                offer_kind="metered_api",
                metadata={
                    "source_url": observation.url,
                    "extracted_from": "data_kind_attribute",
                    "kind": "promo" if model in promo_models else "go",
                    "evidence": "data-kind attribute",
                },
            ))

    # Strategy 4: Find "Nx usage" text near model names in text content
    # First strip HTML tags, then find patterns
    clean_text = re.sub(r'<[^>]+>', ' ', text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    # Pattern: "4,100 GPT 5.6 Luna 2x usage"
    text_multipliers = re.findall(
        r'(\d[\d,]+)\s+([\w\s.\-]+?)\s+(\d+)x\s+usage',
        clean_text
    )
    for count, model_name, mult in text_multipliers:
        model_name = model_name.strip()
        if len(model_name) < 3:
            continue
        mid = "opencode-go/%s" % model_name.lower().replace(" ", "-")
        existing = [o for o in offers if o.model_id == mid]
        if existing:
            existing[0].offer_kind = "usage_multiplier"
            existing[0].usage_multiplier = float(mult)
            existing[0].metadata["multiplier"] = float(mult)
            existing[0].metadata["requests_per_5h"] = int(count.replace(",", ""))
            existing[0].metadata["evidence"] = "text content: %s %s %sx usage" % (count, model_name, mult)
        else:
            offers.append(OfferSnapshot(
                provider_id="opencode-go",
                model_id=mid,
                provider_model_slug=model_name,
                offer_kind="usage_multiplier",
                usage_multiplier=float(mult),
                metadata={
                    "source_url": observation.url,
                    "extracted_from": "text_content",
                    "multiplier": float(mult),
                    "requests_per_5h": int(count.replace(",", "")),
                    "evidence": "text content: %s %s %sx usage" % (count, model_name, mult),
                },
            ))

    return offers
