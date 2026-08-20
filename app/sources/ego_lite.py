"""app/sources/ego_lite.py — Browser adapter using ego-lite (ego-browser skill).

Uses the ego-lite browser for scraping JS-rendered pages, auth-gated dashboards,
and complex multi-step flows. Falls back to urllib for simple pages.

Requires: ego-lite installed, ego-browser skill available to the agent.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso

SOURCE_ID = "ego-lite-browser"
CADENCE_MINUTES = 240  # 4 hours — browser crawling is heavier

# Pages that need browser rendering (JS-heavy, auth-gated, or SPA)
BROWSER_TARGETS = [
    {"url": "https://dev.opencode.ai/go", "name": "opencode-go", "extract": "opencode"},
    {"url": "https://opencode.ai/data", "name": "opencode-data", "extract": "opencode"},
    {"url": "https://huggingface.co/pricing", "name": "hf-pricing", "extract": "pricing"},
    {"url": "https://openrouter.ai/models", "name": "openrouter-models", "extract": "model-list"},
    {"url": "https://cloud.sambanova.ai/apis", "name": "sambanova", "extract": "pricing"},
    {"url": "https://console.groq.com/keys", "name": "groq", "extract": "pricing"},
    {"url": "https://groq.com/pricing", "name": "groq-pricing", "extract": "pricing"},
    {"url": "https://www.novita.ai/pricing", "name": "novita", "extract": "pricing"},
    {"url": "https://deepinfra.com/pricing", "name": "deepinfra", "extract": "pricing"},
    {"url": "https://www.together.ai/pricing", "name": "together", "extract": "pricing"},
    {"url": "https://fireworks.ai/pricing", "name": "fireworks", "extract": "pricing"},
    {"url": "https://siliconflow.cn/pricing", "name": "siliconflow", "extract": "pricing"},
]

DEAL_KEYWORDS = [
    "free", "credit", "bonus", "promo", "discount", "trial",
    "signup", "sign-up", "register", "limited", "launch",
    "multiplier", "2x", "3x", "5x", "10x",
    "$0", "$5", "$10", "$50", "$100", "$200",
]


def _ego_browser_fetch(url: str, timeout: int = 30) -> str | None:
    """Try to use ego-browser skill to fetch a page. Returns page content or None."""
    try:
        # Check if ego-browser skill is available
        result = subprocess.run(
            ["which", "ego-browser"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None

        # Use ego-browser snapshot to get page content
        result = subprocess.run(
            ["ego-browser", "snapshot", url],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


def _http_fetch(url: str) -> str | None:
    """Simple HTTP fetch fallback."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "deal-radar/2.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def fetch() -> list[Observation]:
    observations = []
    for target in BROWSER_TARGETS:
        url = target["url"]
        name = target["name"]

        # Try ego-browser first, fall back to HTTP
        content = _ego_browser_fetch(url)
        source_type = "browser_ego"

        if not content:
            content = _http_fetch(url)
            source_type = "provider_page"

        if content:
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type=source_type,
                url=url,
                fetched_at=now_iso(),
                status=200,
                text=content,
                sha256=sha256(content),
                metadata={"target_name": name, "extract_type": target["extract"]}
            ))
        else:
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type="fetch_failed",
                url=url,
                fetched_at=now_iso(),
                status=None,
                text="FETCH_ERROR: ego-browser and HTTP both failed",
                sha256=sha256("failed"),
                metadata={"target_name": name}
            ))

    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    if observation.status is None or "FETCH_ERROR" in observation.text:
        return []

    text = observation.text
    offers = []
    extract_type = observation.metadata.get("extract_type", "")

    if extract_type == "opencode":
        # Reuse opencode-style extraction: find data-model attributes
        import re
        models = re.findall(r'data-model="([^"]+)"', text)
        for model in models:
            if len(model) < 3:
                continue
            container_pos = text.find(f'data-model="{model}"')
            if container_pos == -1:
                continue
            container = text[container_pos:container_pos + 2000]
            has_promo = bool(re.search(r'2x\s*usage|bonus|multiplier', container, re.IGNORECASE))

            offers.append(OfferSnapshot(
                provider_id=observation.metadata.get("target_name", "unknown"),
                model_id=f"{observation.metadata.get('target_name')}/{model.lower()}",
                provider_model_slug=model,
                offer_kind="usage_multiplier" if has_promo else "metered_api",
                usage_multiplier=2.0 if has_promo else None,
                metadata={"source_url": observation.url, "extracted_from": "ego-browser", "multiplier": 2.0 if has_promo else None}
            ))

    elif extract_type == "model-list":
        # Try to extract model listings from page content
        import re
        # Look for model cards/rows with pricing info
        price_matches = re.findall(r'([\w./:-]+)\s*\$?([\d.]+)\s*/?\s*(?:M|million|1M)', text)
        for model, price in price_matches:
            if len(model) > 3 and len(model) < 80:
                offers.append(OfferSnapshot(
                    provider_id=observation.metadata.get("target_name", "unknown"),
                    model_id=f"{observation.metadata.get('target_name')}/{model.lower().replace('/', '-')}",
                    provider_model_slug=model,
                    offer_kind="metered_api",
                    input_per_m=float(price) if price.replace('.', '').isdigit() else None,
                    metadata={"source_url": observation.url, "extracted_from": "ego-browser"}
                ))

    elif extract_type == "pricing":
        # Generic pricing page extraction
        import re
        # Find dollar amounts near model-like names
        blocks = re.split(r'\n|<br|<p|<div', text)
        for block in blocks:
            dollars = re.findall(r'\$(\d+(?:\.\d+)?)', block)
            if dollars:
                # Check if block mentions free, credit, promo
                is_free = any(w in block.lower() for w in ["free", "$0", "no cost"])
                is_deal = any(w in block.lower() for w in DEAL_KEYWORDS)
                if is_free or is_deal:
                    # Generate synthetic model_id for offers without one
                    target_name = observation.metadata.get("target_name", "unknown")
                    deal_type = "free_tier" if is_free else "deal_signal"
                    synthetic_model_id = f"{target_name}/{deal_type}"
                    
                    offers.append(OfferSnapshot(
                        provider_id=target_name,
                        model_id=synthetic_model_id,
                        provider_model_slug=None,
                        offer_kind=deal_type,
                        metadata={
                            "source_url": observation.url,
                            "extracted_from": "ego-browser",
                            "prices_found": dollars,
                            "is_free": is_free,
                            "deal_keywords": [w for w in DEAL_KEYWORDS if w in block.lower()]
                        }
                    ))

    else:
        # Generic extraction: just look for deal signals
        import re
        for keyword in DEAL_KEYWORDS:
            if keyword.lower() in text.lower():
                # Generate synthetic model_id for offers without one
                target_name = observation.metadata.get("target_name", "unknown")
                synthetic_model_id = f"{target_name}/deal-{keyword}"
                
                offers.append(OfferSnapshot(
                    provider_id=target_name,
                    model_id=synthetic_model_id,
                    provider_model_slug=None,
                    offer_kind="deal_signal",
                    metadata={
                        "source_url": observation.url,
                        "extracted_from": "ego-browser",
                        "keyword": keyword
                    }
                ))
                break  # One deal signal per page is enough

    return offers
