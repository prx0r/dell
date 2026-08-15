#!/usr/bin/env python3
"""app/normalize.py — normalize all LLM-pricing sources into ONE canonical schema.

Ingests:
  litellm  (model_prices_and_context_window.json, 3,040 models, local clone)
  llm-prices (simonw, per-provider price files, local clone)
  awesome-free-llm-apis (data.json, free tiers + rate limits, local clone)
  models.dev (live API, no key)
  openrouter (live API, no key)
  artificial-analysis (OPTIONAL, needs AA_API_KEY)

Canonical output record (the deal-radar DB row):
  {provider, model, prompt_per_token, completion_per_token, cache_read_per_token,
   context, quality_scores:{coding,agentic,intelligence}, free, rpm, rpd, source, updated}
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "canonical-models.json"


def _from_litellm() -> dict:
    p = ROOT / "litellm" / "model_prices_and_context_window.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for mid, rec in d.items():
        if not isinstance(rec, dict):
            continue
        prov = rec.get("litellm_provider", mid.split("/")[0] if "/" in mid else "litellm")
        out[mid] = {
            "provider": prov, "model": mid,
            "prompt_per_token": rec.get("input_cost_per_token", 0) or 0,
            "completion_per_token": rec.get("output_cost_per_token", 0) or 0,
            "cache_read_per_token": rec.get("cache_read_input_token_cost", 0) or 0,
            "context": rec.get("max_input_tokens") or rec.get("max_tokens"),
            "free": False, "rpm": None, "rpd": None, "source": "litellm",
            "updated": int(time.time()),
        }
    return out


def _from_llm_prices() -> dict:
    d = ROOT / "llm-prices" / "data"
    out = {}
    for f in d.glob("*.json"):
        prov = f.stem
        try:
            recs = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(recs, dict):
            recs = recs.get("models", {})
        for mid, rec in (recs.items() if isinstance(recs, dict) else []):
            if not isinstance(rec, dict):
                continue
            out[f"{prov}/{mid}"] = {
                "provider": prov, "model": mid,
                "prompt_per_token": (rec.get("input_cost_per_mtok") or 0) / 1e6,
                "completion_per_token": (rec.get("output_cost_per_mtok") or 0) / 1e6,
                "cache_read_per_token": 0, "context": rec.get("context_length"),
                "free": bool(rec.get("free")), "rpm": None, "rpd": None,
                "source": "llm-prices", "updated": int(time.time()),
            }
    return out


def _from_free_apis() -> dict:
    p = ROOT / "awesome-free-llm-apis" / "data.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    providers = d.get("providers", []) if isinstance(d.get("providers"), list) else []
    for prov in providers:
        name = prov.get("name") or prov.get("provider") or "?"
        for mid, rec in (prov.get("models", {}).items() if isinstance(prov.get("models"), dict) else []):
            out[f"{name}/{mid}"] = {
                "provider": name, "model": mid,
                "prompt_per_token": 0.0, "completion_per_token": 0.0, "cache_read_per_token": 0.0,
                "context": None, "free": True,
                "rpm": rec.get("rate_limit", {}).get("requests_per_minute") if isinstance(rec.get("rate_limit"), dict) else None,
                "rpd": rec.get("rate_limit", {}).get("requests_per_day") if isinstance(rec.get("rate_limit"), dict) else None,
                "source": "awesome-free-llm-apis", "updated": int(time.time()),
            }
    return out


def _from_models_dev() -> dict:
    import urllib.request
    req = urllib.request.Request("https://models.dev/models.json", headers={"User-Agent": "deal-radar/0.1 (mailto:dev@patala.local)"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    out = {}
    for mid, rec in d.items():
        price = rec.get("pricing")
        if not isinstance(price, dict):
            continue
        in_ = float(price.get("input") or 0); out_ = float(price.get("output") or 0)
        if in_ == 0 and out_ == 0:
            continue  # no real price → skip (can't report $0)
        lim = rec.get("limit")
        out[mid] = {
            "provider": mid.split("/")[0], "model": mid,
            "prompt_per_token": in_ / 1e6, "completion_per_token": out_ / 1e6,
            "cache_read_per_token": float(price.get("cache_read") or 0) / 1e6,
            "context": lim.get("context") if isinstance(lim, dict) else None,
            "free": in_ == 0 or out_ == 0, "rpm": None, "rpd": None,
            "source": "models.dev", "updated": int(time.time()),
        }
    return out


def _from_openrouter() -> dict:
    import urllib.request
    req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "deal-radar/0.1 (mailto:dev@patala.local)"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    out = {}
    for m in d.get("data", []):
        p = m.get("pricing", {})
        try:
            in_ = float(p.get("prompt") or 0); out_ = float(p.get("completion") or 0)
        except (TypeError, ValueError):
            continue
        out[m["id"]] = {
            "provider": m["id"].split("/")[0], "model": m["id"],
            "prompt_per_token": in_, "completion_per_token": out_,
            "cache_read_per_token": float(p.get("input_cache_read") or 0),
            "context": m.get("context_length"), "free": ":free" in m["id"],
            "rpm": None, "rpd": None, "source": "openrouter", "updated": int(time.time()),
        }
    return out


def normalize() -> dict:
    """Merge all sources into one canonical model DB. Later sources override same keys' details."""
    merged = {}
    for fn in (_from_litellm, _from_llm_prices, _from_free_apis, _from_models_dev, _from_openrouter):
        try:
            merged.update(fn())
        except Exception as e:
            print(f"  [normalize] source {fn.__name__}: {e}")
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "patala.dealradar.v1", "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "count": len(merged), "models": merged}, indent=1, ensure_ascii=False), encoding="utf-8")
    return merged


if __name__ == "__main__":
    m = normalize()
    print(f"canonical models: {len(m)}")
