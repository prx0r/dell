"""app/sources/context_engineering.py — Agent context patterns from repos.

Mines AGENTS.md, CLAUDE.md, and context engineering patterns from repos.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "context-engineering"
CADENCE_MINUTES = 1440  # 24h
REPOS_TO_MINING = [
    "https://raw.githubusercontent.com/muratcankoylan/Agent-Skills-for-Context-Engineering/main/README.md",
    "https://raw.githubusercontent.com/gsd-build/gsd-2/main/AGENTS.md",
]


def fetch() -> list[Observation]:
    observations = []
    for url in REPOS_TO_MINING:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dell/2.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            text = resp.read().decode("utf-8")
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="repo_readme", url=url,
                fetched_at=now_iso(), status=resp.status, text=text[:50000], sha256=sha256(text),
            ))
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID, source_type="repo_readme", url=url,
                fetched_at=now_iso(), status=None, text=f"FETCH_ERROR: {e}", sha256=sha256(str(e)),
            ))
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract context engineering patterns as informational offers."""
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []

    patterns = []
    text_lower = observation.text.lower()

    pattern_keywords = {
        "context_compilation": ["context", "compile", "curriculum", "playbook"],
        "few_shot_learning": ["few-shot", "in-context", "demonstration", "example"],
        "negative_memory": ["not found", "searched", "absence", "negative"],
        "adaptive_context": ["evolving", "self-improving", "dynamic", "adaptive"],
        "tool_selection": ["tool", "select", "relevant", "filter"],
        "prompt_engineering": ["prompt", "template", "system", "instruction"],
    }

    for pattern_name, keywords in pattern_keywords.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches >= 2:
            patterns.append(OfferSnapshot(
                provider_id="context-pattern",
                model_id=pattern_name,
                provider_model_slug=f"context/{pattern_name}",
                offer_kind="knowledge_pattern",
                metadata={
                    "source": "context-engineering",
                    "url": observation.url,
                    "matches": matches,
                },
            ))

    return patterns
