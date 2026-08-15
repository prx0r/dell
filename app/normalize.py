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
        in_ = out_ = 0.0
        if isinstance(price, dict):
            in_ = float(price.get("input") or 0); out_ = float(price.get("output") or 0)
        # models.dev is the TAGGING source (modalities/capabilities/benchmarks). Keep the record even
        # with null price — enrichment adds these tags to the price-bearing record from other sources.
        lim = rec.get("limit")
        out[mid] = {
            "provider": mid.split("/")[0], "model": mid,
            "prompt_per_token": in_ / 1e6, "completion_per_token": out_ / 1e6,
            "cache_read_per_token": 0.0,
            "context": lim.get("context") if isinstance(lim, dict) else None,
            "free": in_ == 0 or out_ == 0, "rpm": None, "rpd": None,
            # the tagging/modality gold we were dropping (adopt models.dev fully):
            "input_modalities": rec.get("modalities", {}).get("input", []),
            "output_modalities": rec.get("modalities", {}).get("output", []),
            "reasoning": bool(rec.get("reasoning")),
            "tool_call": bool(rec.get("tool_call")),
            "structured_output": bool(rec.get("structured_output")),
            "benchmarks": rec.get("benchmarks", []),
            "license": rec.get("license"),
            "open_weights": bool(rec.get("open_weights")),
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


def _enrich_from_modelsdev(models: dict, md: dict) -> dict:
    """Merge models.dev's richer tagging (modalities/capabilities/benchmarks/license/open_weights)
    into every model record that shares an id or base name, even when a later price source wins."""
    enriched = {}
    for mid, rec in md.items():
        base = mid.split("/")[-1].lower()
        # find any canonical model whose base name matches this models.dev entry
        for cmid, cref in models.items():
            if base in cmid.lower() or cmid.lower().split("/")[-1] in base:
                enriched[cmid] = {
                    **cref,
                    "input_modalities": rec.get("input_modalities", cref.get("input_modalities", [])),
                    "output_modalities": rec.get("output_modalities", cref.get("output_modalities", [])),
                    "reasoning": rec.get("reasoning", cref.get("reasoning", False)),
                    "tool_call": rec.get("tool_call", cref.get("tool_call", False)),
                    "structured_output": rec.get("structured_output", cref.get("structured_output", False)),
                    "benchmarks": rec.get("benchmarks", cref.get("benchmarks", [])),
                    "license": rec.get("license", cref.get("license")),
                    "open_weights": rec.get("open_weights", cref.get("open_weights", False)),
                }
    return enriched


def normalize() -> dict:
    """Merge all sources into one canonical model DB. Later sources override same keys' details,
    but the models.dev tagging (modalities/capabilities/benchmarks) is preserved via _enrich_from_modelsdev."""
    merged = {}
    md = {}
    for fn in (_from_litellm, _from_llm_prices, _from_free_apis, _from_models_dev, _from_openrouter):
        try:
            data = fn()
            if fn == _from_models_dev:
                md = data  # keep for enrichment
            merged.update(data)
        except Exception as e:
            print(f"  [normalize] source {fn.__name__}: {e}")
    merged = _enrich_from_modelsdev(merged, md)
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "patala.dealradar.v1", "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "count": len(merged), "models": merged}, indent=1, ensure_ascii=False), encoding="utf-8")
    return merged


if __name__ == "__main__":
    m = normalize()
    print(f"canonical models: {len(m)}")
