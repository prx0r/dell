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
        
        # Find the pills section which contains the actual model cards
        pills_pos = text.find('data-slot="pills"')
        if pills_pos != -1:
            # Extract 10000 chars after pills to get all model cards
            pills_section = text[pills_pos:pills_pos + 10000]
            
            # Find all data-item elements with data-model and check for data-bonus
            # Pattern: <span ... data-model="modelname" ...>...</span>
            # We need to find the closing </span> that matches the opening <span>
            
            # Find all data-model positions
            for match in re.finditer(r'data-model=\"([^\"]+)\"', pills_section):
                model = match.group(1)
                # Get the context around this model (1000 chars after)
                start = match.start()
                end = min(len(pills_section), start + 1000)
                context = pills_section[start:end]
                
                # Check for data-bonus attribute with multiplier text
                bonus_match = re.search(r'data-bonus[^>]*>(\d+)x\s*(?:usage|bonus|multiplier)', context, re.IGNORECASE)
                if bonus_match:
                    try:
                        mult = float(bonus_match.group(1))
                        model_promos[model] = mult
                    except ValueError:
                        model_promos[model] = None
                else:
                    model_promos[model] = None
        
        existing = set()
        for model in models:
            if len(model) < 3 or model in existing:
                continue
            existing.add(model)
            mid = "opencode-go/%s" % model.lower()
            is_promo = model_promos.get(model)
            
            # Extract the selector for evidence
            selector = '[data-model="%s"]' % model
            if is_promo:
                selector += ' [data-bonus]'
            
            offers.append(OfferSnapshot(
                provider_id="opencode-go",
                model_id=mid,
                provider_model_slug=model,
                offer_kind="usage_multiplier" if is_promo else "metered_api",
                usage_multiplier=is_promo if is_promo else None,
                metadata={
                    "source_url": observation.url,
                    "extracted_from": "playwright_browser",
                    "multiplier": is_promo if is_promo else None,
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
