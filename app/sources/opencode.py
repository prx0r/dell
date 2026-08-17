"""app/sources/opencode.py — OpenCode Go adapter (HIGHEST PRIORITY).

Fetches the OpenCode Go landing page and data page to extract:
- Model identity and pricing
- Multiplier labels (e.g. "2x usage")
- Subscription fee and model-specific allowances
- Input/output/cache prices
- Request estimates
"""
from __future__ import annotations

import json
import re
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "opencode-go"
CADENCE_MINUTES = 120  # 2h

URLS = [
    "https://dev.opencode.ai/go",
    "https://opencode.ai/data",
    "https://opencode.ai",
]

DEAL_KEYWORDS = re.compile(
    r"(free|discount|% off|promo|launch|limited|credits?|bonus|[2-9]x\s*(?:usage|tokens?|quota)|"
    r"signup|off[\s-]peak|price\s*cut|extended|until|through|ends?\s*(?:in|on|at)|"
    r"\$[\d.]+\s*/?\s*(?:mo|month|per))",
    re.IGNORECASE,
)


def fetch() -> list[Observation]:
    """Fetch OpenCode Go pages."""
    observations = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "deal-radar/2.0 (https://github.com/prx0r/garglecum)",
                "Accept": "text/html,application/json",
            })
            resp = urllib.request.urlopen(req, timeout=30)
            text = resp.read().decode("utf-8", errors="replace")
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type="provider_page",
                url=url,
                fetched_at=now_iso(),
                status=resp.status,
                text=text,
                sha256=sha256(text),
                etag=resp.headers.get("ETag"),
                last_modified=resp.headers.get("Last-Modified"),
            ))
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type="provider_page",
                url=url,
                fetched_at=now_iso(),
                status=None,
                text=f"FETCH_ERROR: {e}",
                sha256=sha256(str(e)),
            ))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract OpenCode Go offers from page content."""
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []

    text = observation.text
    offers = []

    # Try to find JSON data in script tags or API responses
    json_blocks = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
    for block in json_blocks:
        if "model" in block.lower() and ("price" in block.lower() or "free" in block.lower()):
            try:
                # Try to parse as JSON
                data = json.loads(block)
                offers.extend(_parse_json_data(data))
            except (json.JSONDecodeError, ValueError):
                pass

    # Try to find pricing tables or cards
    # Look for model names with prices (model names must contain hyphens/underscores, min 5 chars)
    price_patterns = [
        r'(?P<model>[\w][\w./-]{4,})\s*(?:\||:|\s)\s*\$?(?P<input>[\d.]+)\s*/?\s*(?:/\s*M|per\s*M|input)',
        r'(?P<model>[\w][\w./-]{4,})\s*(?:\||:|\s)\s*(?:FREE|free)',
        r'(?P<mult>[2-9]x)\s*(?:usage|tokens?|quota)\s+(?:for|on)\s+(?P<model>[\w][\w./-]{4,})',
    ]

    # Find ALL multiplier mentions in the page (e.g. "2x usage", "data-bonus>2x")
    all_multipliers = re.findall(r'(\d)[x×]\s*(?:usage|tokens?|bonus)', text, re.IGNORECASE)
    
    for pattern in price_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groupdict()
            model = groups.get("model", "")
            if not model or len(model) < 3:
                continue

            # Normalize model name
            if "/" not in model:
                model = f"opencode-go/{model}"

            multiplier = None
            mult_match = re.search(r'([2-9])x', text[max(0, match.start()-50):match.end()+50])
            if mult_match:
                multiplier = float(mult_match.group(1))

            input_price = None
            if groups.get("input"):
                try:
                    input_price = float(groups["input"])
                except ValueError:
                    pass

            offers.append(OfferSnapshot(
                provider_id="opencode-go",
                model_id=model,
                provider_model_slug=model.split("/")[-1],
                offer_kind="provider_route" if multiplier else "metered_api",
                input_per_m=input_price,
                free=input_price == 0 if input_price is not None else False,
                usage_multiplier=multiplier,
                metadata={"source_url": observation.url, "extracted_from": "html_parse",
                          "multiplier_found": bool(all_multipliers)},
            ))

    # CRITICAL: If we found "2x usage" on the page but no model-specific offers,
    # create a general multiplier deal for OpenCode Go
    if all_multipliers and not any(o.usage_multiplier for o in offers):
        mult_value = float(all_multipliers[0])
        offers.append(OfferSnapshot(
            provider_id="opencode-go",
            model_id="opencode-go/2x-usage-promo",
            provider_model_slug="2x-usage",
            offer_kind="usage_multiplier",
            usage_multiplier=mult_value,
            metadata={"source_url": observation.url, "extracted_from": "multiplier_pattern",
                      "multiplier": mult_value, "note": f"Page shows {mult_value}x usage multiplier"},
        ))

    # If no structured data found, DO NOT fabricate known models
    # Adapters are forbidden from providing fallback commercial facts
    # Unknown models remain unknown until observed in actual page content

    return offers


def _parse_json_data(data) -> list[OfferSnapshot]:
    """Try to extract offers from JSON data structures."""
    offers = []
    if isinstance(data, dict):
        # Look for model/pricing arrays
        for key in ("models", "data", "plans", "pricing"):
            if key in data and isinstance(data[key], (list, dict)):
                items = data[key] if isinstance(data[key], list) else data[key].values()
                for item in items:
                    if isinstance(item, dict):
                        model = item.get("id") or item.get("model") or item.get("name")
                        if model:
                            price = item.get("pricing") or item.get("price") or item.get("cost")
                            offers.append(OfferSnapshot(
                                provider_id="opencode-go",
                                model_id=f"opencode-go/{model}" if "/" not in str(model) else str(model),
                                provider_model_slug=str(model),
                                offer_kind="metered_api",
                                input_per_m=float(price) if price else None,
                                free=bool(item.get("free")),
                                metadata={"source_url": "json_parse"},
                            ))
    return offers
