"""app/sources/mcp_registry.py — MCP server registry adapter.

Fetches the MCP server registry for agent tool intelligence.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "mcp-registry"
CADENCE_MINUTES = 1440  # 24h
REGISTRY_URL = "https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/main/README.md"


def fetch() -> list[Observation]:
    try:
        req = urllib.request.Request(REGISTRY_URL, headers={"User-Agent": "dell/2.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        text = resp.read().decode("utf-8")
        return [Observation(source_id=SOURCE_ID, source_type="repo_readme", url=REGISTRY_URL,
                            fetched_at=now_iso(), status=resp.status, text=text[:100000], sha256=sha256(text))]
    except Exception as e:
        return [Observation(source_id=SOURCE_ID, source_type="repo_readme", url=REGISTRY_URL,
                            fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)))]


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract MCP server entries as capability offers."""
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []

    offers = []
    lines = observation.text.split("\n")
    current_category = ""

    for line in lines:
        if line.startswith("### "):
            current_category = line[4:].strip()
        elif line.startswith("- [") or line.startswith("  - ["):
            # Parse MCP server entry
            name_end = line.find("](")
            if name_end > 0:
                name = line[line.find("[")+1:name_end]
                url_start = line.find("](") + 2
                url_end = line.find(")", url_start)
                url = line[url_start:url_end] if url_end > url_start else ""

                offers.append(OfferSnapshot(
                    provider_id="mcp-server",
                    model_id=name,
                    provider_model_slug=f"mcp/{name}",
                    offer_kind="agent_tool",
                    metadata={
                        "source": "mcp-registry",
                        "category": current_category,
                        "url": url,
                    },
                ))

    return offers
