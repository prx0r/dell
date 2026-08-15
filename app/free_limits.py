#!/usr/bin/env python3
"""app/free_limits.py — the free-tier rate-limit registry (parsed from awesome-free-llm-apis).

The awesome-free-llm-apis data.json carries per-model rate limits like "15 RPM, 20K TPD" for the
free tiers. This parses them into a provider/model → (rpm, rpd, tokens_per_day) map, so the router can
be RATE-LIMIT-AWARE: a free model with a tiny quota that can't serve a batch workload is penalized
(because free ≠ good if it can't handle the volume).

Format examples: "15 RPM, 20K TPD", "30 req/min, 1M TPD", "1 RPD".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "awesome-free-llm-apis" / "data.json"


def _parse_rate(text: str) -> dict:
    """Parse a rate-limit string like '15 RPM, 20K TPD' → {rpm, rpd, tokens_per_day}."""
    t = (text or "").lower()
    rpm = rpd = tpd = None
    # rpm: N rpm / N req per min / N r/m
    m = re.search(r"(\d+)\s*(?:rpm|req(?:uests)?\s*/?\s*min|r/min|req/min)", t)
    if m:
        rpm = int(m.group(1))
    # rpd: N rpd / N req per day / N requests/day
    m = re.search(r"(\d+)\s*(?:rpd|req(?:uests)?\s*/?\s*day|requests?/day|/day)", t)
    if m:
        rpd = int(m.group(1))
    # tpd: N tpd / Nk tpd / N tokens per day
    m = re.search(r"(\d+)\s*[km]?\s*(?:tpd|tokens?\s*(?:per\s*)?day|tok\s*/?\s*day)", t)
    if m:
        val = int(m.group(1))
        if "k" in t[: m.end()] and m.group(0).count("k"):
            val *= 1000
        tpd = val
    return {"rpm": rpm, "rpd": rpd, "tokens_per_day": tpd}


def load() -> dict:
    """provider → {model: {rpm,rpd,tokens_per_day}} from the free-apis data."""
    try:
        d = json.loads(SRC.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for prov in d.get("providers", []):
        name = (prov.get("name") or prov.get("provider") or "").lower()
        models = prov.get("models") or []
        prov_limits = {}
        if isinstance(models, list):
            for m in models:
                if not isinstance(m, dict):
                    continue
                mid = m.get("id") or m.get("name")
                rl = m.get("rateLimit")
                if mid and rl:
                    prov_limits[mid.lower()] = _parse_rate(rl)
        if prov_limits or name:
            out[name] = {"models": prov_limits, "name": name}
    return out


def rate_limit_for(provider: str, model: str) -> dict:
    """The rate limit for a model, matched by provider prefix + model base name."""
    reg = load()
    p = provider.lower()
    base = model.split("/")[-1].lower()
    # exact provider match
    rec = reg.get(p)
    if rec:
        rl = rec["models"].get(model.lower()) or rec["models"].get(base)
        if rl:
            return rl
    # fuzzy provider match
    for pname, rec in reg.items():
        if p in pname or pname in p:
            rl = rec["models"].get(base) or rec["models"].get(model.lower())
            if rl:
                return rl
    return {"rpm": None, "rpd": None, "tokens_per_day": None}


def known_limits() -> dict:
    """All parsed per-model rate limits (for the LLM data structure)."""
    reg = load()
    out = {}
    for prov, rec in reg.items():
        for model, rl in rec["models"].items():
            out[f"{prov}/{model}"] = rl
    return out


if __name__ == "__main__":
    d = known_limits()
    print(f"parsed per-model rate limits: {len(d)}")
    for k, v in list(d.items())[:5]:
        print(f"  {k}: {v}")
