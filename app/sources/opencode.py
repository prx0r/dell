"""app/sources/opencode.py — OpenCode Go adapter (uses playwright for JS-rendered pages)."""
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

    # Strategy 1: Find data-model attributes with 2x usage (from playwright)
    if observation.source_type == "browser_page":
        # Find models with data-model attribute
        models = re.findall(r'data-model="([^"]+)"', text)
        # Find which models have 2x usage nearby
        two_x_models = set()
        for m in re.finditer(r'2x\s*usage', text, re.IGNORECASE):
            nearby = text[max(0, m.start()-500):m.start()+500]
            for model in re.findall(r'data-model="([^"]+)"', nearby):
                two_x_models.add(model)

        existing = set()
        for model in models:
            if len(model) < 3 or model in existing:
                continue
            existing.add(model)
            mid = "opencode-go/%s" % model.lower()
            is_promo = model in two_x_models

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
                    "evidence": "data-model=%s with 2x usage" % model if is_promo else "data-model=%s" % model,
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
