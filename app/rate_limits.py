#!/usr/bin/env python3
"""app/rate_limits.py — per-provider rate + token limits (esp. the free tiers).

The router needs to know HOW MUCH each provider gives you, not just the price. This aggregates:
  - the free-tier rate limits (rpm/rpd/tokens) from awesome-free-llm-apis
  - known free-tier daily quotas for the big commercial free APIs (Groq, Z.AI, Cloudflare, OpenRouter-free)
  - the compute-source classes (WebLLM unlimited, Kaggle batch, etc.)
So an agent can answer "how many requests/tokens can I get from the free pool today?" and the router
knows when to swap (a provider's daily quota exhausted → next tier).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# the big free-tier daily quotas (per provider, from their docs/verified research)
FREE_QUOTAS = {
    "groq": {"rpm": 30, "rpd": 1000, "tokens_per_day": 100000, "models": "llama-3.1-8b(14.4k RPD/500k TPD), llama-3.3-70b/gpt-oss(1k RPD)"},
    "z-ai": {"rpm": None, "rpd": None, "tokens_per_day": None, "note": "GLM-4.7-Flash + GLM-4.6V-Flash free tier"},
    "cloudflare": {"rpm": None, "rpd": None, "tokens_per_day": None, "note": "10,000 neurons/day free (Workers AI)"},
    "openrouter": {"rpm": 20, "rpd": 50, "tokens_per_day": None, "note": "50 free-model RPD w/o $10 credit; 1000 RPD with"},
    "kilo": {"rpm": 200, "rpd": None, "tokens_per_day": None, "note": "200 requests/hour/IP on kilo-auto/free"},
    "nvidia-nim": {"rpm": None, "rpd": None, "tokens_per_day": None, "note": "free prototyping endpoints"},
    "ovh": {"rpm": 2, "rpd": None, "tokens_per_day": None, "note": "2 requests/min per IP per model, anonymous"},
    "modelscope": {"rpm": None, "rpd": 2000, "tokens_per_day": None, "note": "~2,000 free requests/day"},
    "mistral": {"rpm": None, "rpd": None, "tokens_per_day": None, "note": "$10/mo free API credits"},
    "cerebras": {"rpm": None, "rpd": None, "tokens_per_day": None, "note": "$5 signup credits"},
    "sarvam": {"rpm": 60, "rpd": None, "tokens_per_day": None, "note": "Sarvam-30B/105B free + ₹1,000 credits"},
}


def load_from_free_apis() -> dict:
    """The per-model rate limits from awesome-free-llm-apis data.json."""
    p = ROOT / "awesome-free-llm-apis" / "data.json"
    out = {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        for prov in d.get("providers", []):
            name = prov.get("name") or prov.get("provider") or "?"
            rl = prov.get("rate_limit") or {}
            models = prov.get("models", {})
            out[name] = {
                "provider": name,
                "rpm": rl.get("requests_per_minute") or rl.get("rpm"),
                "rpd": rl.get("requests_per_day") or rl.get("rpd"),
                "tokens_per_day": rl.get("tokens_per_day"),
                "model_count": len(models) if isinstance(models, dict) else 0,
            }
    except Exception:
        pass
    return out


def all_rate_limits() -> dict:
    """The combined per-provider rate limits (known free quotas + free-apis registry)."""
    return {"providers": FREE_QUOTAS, "from_free_apis": load_from_free_apis()}


def provider_quota(provider: str) -> dict:
    """The quota for one provider (known free quota merged with the free-apis registry)."""
    known = FREE_QUOTAS.get(provider, {})
    apis = load_from_free_apis().get(provider, {})
    return {**known, **apis}


if __name__ == "__main__":
    import json as _j
    rl = all_rate_limits()
    print(_j.dumps({"known_providers": list(rl["providers"].keys()),
                    "free_apis_providers": len(rl["from_free_apis"])}, indent=1))
