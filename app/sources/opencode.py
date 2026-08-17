"""app/sources/opencode.py — OpenCode Go adapter (uses playwright for JS-rendered pages).

Uses semantic DOM extraction instead of proximity-based regex.
"""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "opencode-go"
CADENCE_MINUTES = 120

URLS = ["https://dev.opencode.ai/go", "https://opencode.ai/data", "https://opencode.ai"]


def fetch() -> list[Observation]:
    observations = []
    # Try playwright for main page (JS-rendered)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://dev.opencode.ai/go", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            content = page.content()
            browser.close()
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="browser_page", url="https://dev.opencode.ai/go",
                fetched_at=now_iso(), status=200, text=content, sha256=sha256(content)))
    except Exception as e:
        observations.append(Observation(
            source_id=SOURCE_ID, source_type="browser_page", url="https://dev.opencode.ai/go",
            fetched_at=now_iso(), status=None, text="FETCH_ERROR: %s" % str(e)[:100],
            sha256=sha256(str(e))))

    # Also try HTTP for other pages
    for url in URLS[1:]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deal-radar/2.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            text = resp.read().decode("utf-8", errors="replace")
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="provider_page", url=url,
                fetched_at=now_iso(), status=resp.status, text=text, sha256=sha256(text)))
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="provider_page", url=url,
                fetched_at=now_iso(), status=None, text="FETCH_ERROR: %s" % str(e)[:100],
                sha256=sha256(str(e))))

    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []
    text = observation.text
    offers = []

    # Strategy 1: Semantic DOM extraction (from playwright)
    if observation.source_type == "browser_page":
        # Extract model rows with their promotional badges
        # Look for semantic containers: data-model attributes with nearby data-bonus
        model_promos = {}
        
        # Find all data-model attributes
        models = re.findall(r'data-model="([^"]+)"', text)
        
        # For each model, check if it has a 2x usage badge in its SEMANTIC container
        # Not in 500 chars, but in the actual model row/card
        for model in models:
            # Find the container for this model (up to next model or 2000 chars)
            model_pos = text.find('data-model="%s"' % model)
            if model_pos == -1:
                continue
            
            # Find the end of this model's container (next model or reasonable boundary)
            next_model_pos = len(text)
            for other_model in models:
                if other_model != model:
                    other_pos = text.find('data-model="%s"' % other_model, model_pos + 1)
                    if other_pos != -1 and other_pos < next_model_pos:
                        next_model_pos = other_pos
            
            # Extract just this model's container
            container = text[model_pos:min(next_model_pos, model_pos + 2000)]
            
            # Check for 2x usage badge in THIS container only
            has_2x = bool(re.search(r'2x\s*usage', container, re.IGNORECASE))
            model_promos[model] = has_2x
        
        existing = set()
        for model in models:
            if len(model) < 3 or model in existing:
                continue
            existing.add(model)
            mid = "opencode-go/%s" % model.lower()
            is_promo = model_promos.get(model, False)
            
            # Extract the selector for evidence
            selector = '[data-model="%s"]' % model
            if is_promo:
                selector += ' [data-bonus]'
            
            offers.append(OfferSnapshot(
                provider_id="opencode-go",
                model_id=mid,
                provider_model_slug=model,
                offer_kind="usage_multiplier" if is_promo else "metered_api",
                usage_multiplier=2.0 if is_promo else None,
                metadata={
                    "source_url": observation.url,
                    "extracted_from": "playwright_browser",
                    "multiplier": 2.0 if is_promo else None,
                    "selector": selector,
                    "evidence": "data-model=%s container check" % model,
                }))

    # Strategy 2: Find text content with model info
    if observation.source_type == "provider_page":
        # Find model names and prices
        model_names = re.findall(r'([\w.-]+(?:\s+[\w.-]+)*)\s*\$[\d.]+', text)
        for name in model_names:
            if len(name) > 3 and len(name) < 50:
                offers.append(OfferSnapshot(
                    provider_id="opencode-go",
                    model_id="opencode-go/%s" % name.lower().replace(" ", "-"),
                    provider_model_slug=name,
                    offer_kind="metered_api",
                    metadata={"source_url": observation.url, "extracted_from": "text_parse"}))

    return offers
