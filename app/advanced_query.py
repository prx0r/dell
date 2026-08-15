#!/usr/bin/env python3
"""app/advanced_query.py — the natural-language query router (usage-profile aware).

Handles advanced queries like "I need an image model for batch work" vs "I need an image model for
4 calls/day". These differ in USAGE PROFILE, which changes the routing priority:

  BATCH / high-volume   → rate-limit + free-quota + cheap-per-call matter most
                          (you'll hammer the provider daily; a low rpm/rpd kills you)
  INTERACTIVE / low-vol → quality matters most (a few calls/day; pay for the best)

It infers the profile from the query, then applies the arXiv utility argmax (routing.py) with the
RIGHT weights, and cross-references the per-provider rate limits (rate_limits.py) + free pool
(compute_sources.py).

Pipeline: parse(query) → {task, modality, volume, daily_calls, quality_needed}
          → recommend with volume-tuned λ (cost weight) + rate-limit-aware ranking
          → annotate each pick with: rate_limit (rpm/rpd), free_quota, whether it survives daily calls
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import routing
import rate_limits


def parse(query: str) -> dict:
    """Infer the usage profile from a natural-language query."""
    q = query.lower()
    # task
    task = "coding"
    if any(w in q for w in ("reason", "logic", "thinking", "solve", "proof")):
        task = "reasoning"
    elif any(w in q for w in ("research", "write", "prose", "essay", "summarize", "summary", "report")):
        task = "research"
    elif any(w in q for w in ("extract", "parse", "classify", "tag", "batch", "ocr", "json")):
        task = "extraction"
    elif any(w in q for w in ("long context", "long-context", "100k", "200k", "1m", "big document")):
        task = "long-context"
    # modality
    modality = None
    if any(w in q for w in ("image", "vision", "visual", "photo", "multimodal")):
        modality = "image"
    elif any(w in q for w in ("audio", "speech", "voice", "transcrib")):
        modality = "audio"
    # volume / batch vs interactive
    batch = any(w in q for w in ("batch", "bulk", "large", "many", "thousand", "million", "high volume", "volume"))
    daily = None
    m = re.search(r"(\d+)\s*(?:calls|requests|queries|images|pages|docs)\s*(?:/\s*(?:day|daily)|per\s*day|daily|a\s*day)", q)
    if m:
        daily = int(m.group(1))
    # quality
    quality = "high" if any(w in q for w in ("best", "frontier", "quality", "accurate", "precise", "good")) else "auto"
    return {"task": task, "modality": modality, "batch": batch, "daily_calls": daily,
            "quality": quality, "query": query}


def _provider_of(model: str) -> str:
    m = model.lower()
    # map model-prefix → the free-quota provider key (fuzzy)
    for key in ("groq", "cloudflare", "openrouter", "kilo", "ovh", "modelscope", "mistral",
                "cerebras", "sarvam", "z-ai", "nvidia"):
        if key in m or key.replace("-", "") in m:
            return key if key != "z-ai" else "z-ai"
    return model.split("/")[0]


def recommend_for_query(query: str, limit: int = 5) -> dict:
    """The advanced query router: parse → profile → volume-tuned recommendation + rate-limit-aware.
    Delegates to analyze() for the full algorithm reasoning."""
    return analyze(query, limit=limit)


if __name__ == "__main__":
    import sys as _s
    q = _s.argv[1] if len(_s.argv) > 1 else "I need an image model for batch work"
    res = recommend_for_query(q, limit=4)
    print(f"QUERY: {q}")
    print(f"  profile: {res['profile']}")
    print(f"  strategy: {res['volume_strategy']}")
    for p in res["picks"][:4]:
        print(f"    {p['model'][:38]:<40} free={p['free']} q={p['q']} cost=${p['cost']:.5f} "
              f"rpm={p['rpm']} rpd={p['rpd']} fits_daily={p['fits_daily_volume']}")


def analyze(query: str, limit: int = 5) -> dict:
    """The algorithm's COMPLETE reasoning for a query — gives the LLM the moat's computed
    intelligence (usage profile + volume strategy + per-model utility/value/task-fit + rate-limit)
    so it can reason fast without re-deriving everything. Returns both the algorithm's picks AND
    the reasoning that produced them (the 'why')."""
    profile = parse(query)
    batch = profile["batch"] or (profile["daily_calls"] is not None and profile["daily_calls"] > 50)
    interactive = (profile["daily_calls"] is not None and profile["daily_calls"] <= 50)
    lambda_ = 0.2 if batch else (0.02 if interactive else 0.05)
    r = routing.recommend(task=profile["task"], lambda_=lambda_, limit=50,
                          require_modality=profile["modality"],
                          daily_calls=profile["daily_calls"], volume_importance=0.4)
    quotas = rate_limits.all_rate_limits()
    picks = []
    for p in r["picks"][:limit]:
        prov = _provider_of(p["model"])
        q = quotas.get("providers", {}).get(prov, {})
        rpm, rpd = q.get("rpm"), q.get("rpd")
        fits = True
        if profile["daily_calls"] and rpd is not None:
            fits = profile["daily_calls"] <= rpd
        # the moat: utility + value (quality/cost) so the LLM sees WHY each ranks where it does
        value = (p["q"] / p["cost"]) if p["cost"] > 0 else float("inf")
        picks.append({**{k: p[k] for k in ("model", "provider", "free", "q", "cost")},
                      "utility": p.get("utility"), "value": round(value, 1) if value != float("inf") else "inf",
                      "rpm": rpm, "rpd": rpd, "fits_daily_volume": fits,
                      "reason": _reason(profile, p, value, fits)})
    return {
        "query": query,
        "profile": profile,           # what the algorithm inferred about the need
        "strategy": "batch → free/cheap first + rate-limit aware" if batch
                    else ("interactive → quality first" if interactive else "balanced"),
        "volume_strategy": "batch → free/cheap first + rate-limit aware" if batch
                           else ("interactive → quality first" if interactive else "balanced"),
        "algorithm": r.get("algorithm"),
        "picks": picks,               # ordered by the algorithm's utility (free-first, then value)
        "note": "The picks are ordered by the algorithm's utility (free first, then value/quality). "
                "Each has a 'reason' — the LLM can trust the ordering or reason further from the data.",
    }


def _reason(profile, p, value, fits) -> str:
    """A human/LLM-readable 'why' for each pick (the moat's explanation)."""
    parts = []
    if p["free"]:
        parts.append("FREE — zero cost, you gain from it")
    if p.get("q") is not None:
        parts.append(f"quality {p['q']}")
    if p["cost"] > 0:
        parts.append(f"${p['cost']:.4f}/task")
    if profile["modality"]:
        parts.append(f"{profile['modality']}-capable")
    if profile["batch"]:
        parts.append("batch-friendly")
    if not p["free"] and fits is False:
        parts.append("WARNING: exceeds the provider's daily free quota")
    return "; ".join(parts)
