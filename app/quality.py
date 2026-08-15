#!/usr/bin/env python3
"""app/quality.py — the value engine: cost-per-task + quality + frontiers + deals.

The clever part (per the reference): don't rank by $/M tokens. Compute:
  effective_cost = cost_per_job / success_rate        (a model that needs 3 attempts costs more)
  value_score    = quality / effective_cost           (the frontier we rank by)

Quality comes from the artificial-analysis API (coding/agentic/intelligence scores) when a key is
present; otherwise a conservative fallback. Then derive the PARETO FRONTIERS + DEALS a router cares
about: cheapest, best value, best free, biggest quota, price-crash/new-free alerts.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB = DATA / "canonical-models.json"
AA_KEY = os.environ.get("AA_API_KEY", "")

# conservative per-family quality fallback (0-100) when artificial-analysis is unavailable
FAMILY_QUALITY = {
    "deepseek": {"coding": 78, "agentic": 72, "intelligence": 75},
    "gpt": {"coding": 90, "agentic": 86, "intelligence": 92},
    "claude": {"coding": 88, "agentic": 85, "intelligence": 89},
    "gemini": {"coding": 84, "agentic": 80, "intelligence": 87},
    "qwen": {"coding": 74, "agentic": 68, "intelligence": 70},
    "llama": {"coding": 70, "agentic": 65, "intelligence": 68},
    "kimi": {"coding": 72, "agentic": 66, "intelligence": 70},
    "glm": {"coding": 71, "agentic": 64, "intelligence": 69},
    "mixtral": {"coding": 66, "agentic": 60, "intelligence": 64},
    "mistral": {"coding": 68, "agentic": 62, "intelligence": 66},
    "nemotron": {"coding": 76, "agentic": 70, "intelligence": 72},
    "minimax": {"coding": 70, "agentic": 65, "intelligence": 67},
    "mimo": {"coding": 72, "agentic": 66, "intelligence": 69},
}
DEFAULT_Q = {"coding": 60, "agentic": 55, "intelligence": 58}


def _family(model: str) -> str:
    m = model.lower()
    for fam in FAMILY_QUALITY:
        if fam in m:
            return fam
    return ""


def quality_for(model: str, provider: str = "") -> dict:
    fam = _family(model)
    return FAMILY_QUALITY.get(fam, DEFAULT_Q)


def fetch_aa_quality() -> dict:
    """Optional artificial-analysis quality scores (coding/agentic/intelligence per model)."""
    if not AA_KEY:
        return {}
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://artificialanalysis.ai/api/v2/language/models/free",
            headers={"Authorization": f"Bearer {AA_KEY}", "User-Agent": "deal-radar/0.1"})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        out = {}
        for m in d.get("data", d if isinstance(d, list) else []):
            mid = m.get("model") or m.get("name")
            if mid:
                out[mid] = {"coding": m.get("coding_score"), "agentic": m.get("agentic_score"),
                            "intelligence": m.get("intelligence_index")}
        return out
    except Exception:
        return {}


def cost_per_job(rec: dict, input_tok: int = 20000, output_tok: int = 4000,
                 reasoning_tok: int = 0, cache_read_tok: int = 0) -> float:
    """cost($) for a typical job (20k in / 4k out) using the model's real prices."""
    return (input_tok * rec.get("prompt_per_token", 0)
            + output_tok * rec.get("completion_per_token", 0)
            + reasoning_tok * 0
            + cache_read_tok * rec.get("cache_read_per_token", 0))


def value_score(rec: dict, quality: dict, success_rate: float = 0.85) -> dict:
    """effective_cost = cost/success; value = quality/effective_cost."""
    quality_total = (quality.get("coding", 60) * 0.4 + quality.get("agentic", 55) * 0.3
                     + quality.get("intelligence", 58) * 0.3)
    cj = cost_per_job(rec)
    eff = cj / success_rate if success_rate > 0 else float("inf")
    val = quality_total / eff if eff > 0 else 0.0
    return {"quality": round(quality_total, 1), "cost_per_job": round(cj, 8),
            "effective_cost": round(eff, 8), "value": round(val, 2),
            "free": rec.get("free", False)}


def frontiers(limit: int = 8, mode: str = "chat") -> dict:
    """The Pareto frontiers: best value / cheapest / best free / biggest quota.
    mode='chat' filters to text-chat models (drops image/audio/embedding models)."""
    db = json.loads(DB.read_text(encoding="utf-8"))
    models = db.get("models", {})
    aa = fetch_aa_quality()
    scored = []
    for mid, rec in models.items():
        if mode == "chat":
            # drop image/audio/embedding/retrieval-ish models
            low = mid.lower()
            if any(x in low for x in ("embedding", "embed", "audio", "tts", "stt", "image",
                                      "stable-diffusion", "flux", "dall-e", "sdxl", "whisper",
                                      "/e5-", "bge-", "rerank", "colbert", "retriever", "galactica",
                                      "moderation", "safety", "guard")):
                continue
            ctx = rec.get("context")
            if isinstance(ctx, (int, float)) and ctx < 2048:
                continue
        q = aa.get(mid, quality_for(mid, rec.get("provider", "")))
        vs = value_score(rec, q)
        if rec.get("prompt_per_token", 0) == 0 and rec.get("completion_per_token", 0) == 0 and not rec.get("free"):
            continue
        scored.append({"model": mid, "provider": rec.get("provider"), **vs,
                       "context": rec.get("context"), "rpm": rec.get("rpm"), "rpd": rec.get("rpd"),
                       "source": rec.get("source")})
    paid = [s for s in scored if not s["free"] and s["cost_per_job"] > 0]
    free = [s for s in scored if s["free"] or s["cost_per_job"] == 0]
    return {
        "best_value_paid": sorted(paid, key=lambda s: -s["value"])[:limit],
        "cheapest_paid": sorted(paid, key=lambda s: s["cost_per_job"])[:limit],
        "best_quality": sorted(paid, key=lambda s: -s["quality"])[:limit],
        "best_free": sorted(free, key=lambda s: -s["quality"])[:limit],
        "biggest_free_quota": sorted(free, key=lambda s: (s["rpd"] or 0), reverse=True)[:limit],
    }


def deals() -> dict:
    """The deals layer: recurring-free / subsidy / promo signals from the sources."""
    db = json.loads(DB.read_text(encoding="utf-8"))
    models = db.get("models", {})
    free_models = [{"model": m, "provider": r.get("provider"), "rpm": r.get("rpm"), "rpd": r.get("rpd"),
                    "source": r.get("source")} for m, r in models.items()
                   if r.get("free") or (r.get("prompt_per_token", 0) == 0 and r.get("completion_per_token", 0) == 0)]
    return {"recurring_free_models": free_models, "note": "free-tier models from awesome-free-llm-apis + openrouter :free + $0 sources"}


if __name__ == "__main__":
    print(json.dumps({"frontiers": frontiers(), "deals_count": len(deals()["recurring_free_models"])},
                     indent=1, default=str)[:1200])
