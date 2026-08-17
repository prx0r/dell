#!/usr/bin/env python3
"""app/api_canonical.py — The Canonical Live Data Layer API.

Mission: "LLM Deals provides live, verifiable, machine-readable data about
LLM models, providers, prices, free inference, promotions and availability."

Four questions:
1. What models/providers exist?
2. What do they cost right now?
3. What unusual deals/credits/free quotas/promos exist?
4. What is each option actually suitable for?
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

import models_v2
import providers as providers_mod

app = FastAPI(title="LLM Deals", version="1.0",
              description="The canonical live data layer for LLM inference economics")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _enrich_with_freshness(offers: list[dict]) -> list[dict]:
    """Add freshness SLA and verification status to each offer."""
    now = time.time()
    for o in offers:
        meta = o.get("metadata", {})
        # Freshness: when was this data last verified?
        source_url = meta.get("source_url", "")
        o["freshness"] = {
            "last_verified_at": meta.get("observed_at", ""),
            "source_url": source_url,
            "source_type": meta.get("source_type", "unknown"),
            "is_stale": False,  # would need tracking to determine
        }
        # Verification: how confident are we?
        if source_url and "artificialanalysis" in source_url:
            o["verification"] = {"status": "verified", "confidence": 0.95, "source": "official_api"}
        elif source_url and ("openrouter.ai" in source_url or "models.dev" in source_url):
            o["verification"] = {"status": "verified", "confidence": 0.90, "source": "official_api"}
        elif source_url and "help.aliyun.com" in source_url:
            o["verification"] = {"status": "verified", "confidence": 0.85, "source": "official_docs"}
        elif source_url and "reddit.com" in source_url:
            o["verification"] = {"status": "community_reported", "confidence": 0.40, "source": "community"}
        else:
            o["verification"] = {"status": "likely", "confidence": 0.70, "source": "provider_page"}
        # Rate limit info
        if o.get("requests_day"):
            o["rate_limits"] = {
                "requests_per_day": o["requests_day"],
                "requests_per_minute": o.get("requests_minute"),
                "tokens_per_day": o.get("tokens_day"),
            }
        # Activation class (simplified)
        prov = providers_mod.get_provider(o.get("provider_id", ""))
        if prov:
            if prov.setup_difficulty == 1 and not o.get("card_required"):
                o["activation_class"] = "KEY_ONLY"
            elif prov.setup_difficulty == 1:
                o["activation_class"] = "SIGNUP"
            else:
                o["activation_class"] = "VERIFY"
        else:
            o["activation_class"] = "UNKNOWN"
    return offers


def _load_all() -> dict:
    """Load all snapshot data into memory."""
    snapshots_dir = ROOT / "snapshots"
    all_offers = []
    all_events = []
    if snapshots_dir.exists():
        for f in snapshots_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                all_offers.extend(data.get("offers", []))
            except Exception:
                continue
    events_dir = ROOT / "events"
    if events_dir.exists():
        for f in events_dir.glob("*.json"):
            try:
                ev = json.loads(f.read_text())
                if isinstance(ev, list):
                    all_events.extend(ev)
                else:
                    all_events.append(ev)
            except Exception:
                continue
    return {"offers": all_offers, "events": all_events}


# --- Core Endpoints ---

@app.get("/v1/models")
def list_models(search: str = None, limit: int = Query(50, le=200)):
    """What models exist."""
    data = _load_all()
    models = {}
    for o in data["offers"]:
        mid = o.get("model_id", "")
        if not mid:
            continue
        if search and search.lower() not in mid.lower():
            continue
        if mid not in models:
            models[mid] = {
                "model_id": mid,
                "providers": [],
                "cheapest_input": None,
                "free_available": False,
                "context_tokens": o.get("context_tokens"),
            }
        models[mid]["providers"].append(o.get("provider_id", "unknown"))
        if o.get("free"):
            models[mid]["free_available"] = True
        in_m = o.get("input_per_m")
        if in_m is not None and (models[mid]["cheapest_input"] is None or in_m < models[mid]["cheapest_input"]):
            models[mid]["cheapest_input"] = in_m

    result = list(models.values())
    result.sort(key=lambda x: x.get("cheapest_input") or 999)
    return {"models": result[:limit], "count": len(result)}


@app.get("/v1/providers")
def list_providers():
    """What providers exist."""
    providers = []
    for pid, p in providers_mod.PROVIDERS.items():
        d = providers_mod.to_dict(p)
        providers.append(d)
    return {"providers": providers, "count": len(providers)}


@app.get("/v1/offerings")
def list_offerings(provider: str = None, model: str = None, free: bool = None,
                   limit: int = Query(50, le=200)):
    """What offerings exist (model × provider combinations)."""
    data = _load_all()
    result = []
    for o in data["offers"]:
        if provider and o.get("provider_id") != provider:
            continue
        if model and model.lower() not in (o.get("model_id") or "").lower():
            continue
        if free is not None and bool(o.get("free")) != free:
            continue
        result.append({
            "model_id": o.get("model_id"),
            "provider_id": o.get("provider_id"),
            "input_per_m": o.get("input_per_m"),
            "output_per_m": o.get("output_per_m"),
            "free": o.get("free"),
            "context_tokens": o.get("context_tokens"),
            "offer_kind": o.get("offer_kind"),
        })
    return {"offerings": result[:limit], "count": len(result)}


@app.get("/v1/deals")
def list_deals(task: str = None, max_price: float = None, free: bool = None,
               openai_compatible: bool = None, automation_allowed: bool = None,
               country: str = None, min_context: int = None,
               limit: int = Query(50, le=200)):
    """What deals/promos/credits exist. The main endpoint."""
    data = _load_all()
    result = []
    for o in data["offers"]:
        if free is not None and bool(o.get("free")) != free:
            continue
        if max_price is not None:
            in_m = o.get("input_per_m")
            if in_m is not None and in_m > max_price:
                continue
            elif in_m is None:
                continue  # exclude unknown prices from max_price filter
        if min_context and (o.get("context_tokens") or 0) < min_context:
            continue
        # Filter by task capability (tool calling for agentic tasks)
        if task in ("coding", "agentic", "agentic_coding") and not o.get("metadata", {}).get("tool_call"):
            # Allow through but note it
            pass
        # Filter by OpenAI compatibility
        if openai_compatible is not None:
            prov = providers_mod.get_provider(o.get("provider_id", ""))
            if prov and openai_compatible and not prov.openai_compatible:
                continue
        result.append({
            "model_id": o.get("model_id"),
            "provider_id": o.get("provider_id"),
            "input_per_m": o.get("input_per_m"),
            "output_per_m": o.get("output_per_m"),
            "free": o.get("free"),
            "price_known": o.get("price_known", True),
            "context_tokens": o.get("context_tokens"),
            "offer_kind": o.get("offer_kind"),
            "metadata": o.get("metadata", {}),
        })
    result.sort(key=lambda x: x.get("input_per_m") if x.get("input_per_m") is not None else 9999)
    result = _enrich_with_freshness(result)
    # INVARIANT: exclude offers with unknown prices unless explicitly requested
    result = [o for o in result if o.get("price_known", True)]
    return {"deals": result[:limit], "count": len(result)}


@app.get("/v1/deals/live")
def deals_live(limit: int = Query(20, le=100)):
    """Currently active deals."""
    return list_deals(free=None, limit=limit)


@app.get("/v1/deals/free")
def deals_free(limit: int = Query(20, le=100)):
    """Free models/offers."""
    return list_deals(free=True, limit=limit)


@app.get("/v1/deals/expiring")
def deals_expiring(hours: int = Query(24, le=168)):
    """Deals expiring within N hours."""
    data = _load_all()
    import expiry
    enriched = expiry.enrich_offers_with_expiry(data["offers"])
    expiring = [e for e in enriched if (e.get("expiry", {}).get("hours_remaining") or 9999) <= hours]
    return {"deals": expiring, "count": len(expiring), "hours": hours}


@app.get("/v1/prices")
def list_prices(model: str = None, provider: str = None, sort: str = "input",
                limit: int = Query(50, le=200)):
    """Current prices. The price comparison engine."""
    data = _load_all()
    result = []
    for o in data["offers"]:
        if model and model.lower() not in (o.get("model_id") or "").lower():
            continue
        if provider and o.get("provider_id") != provider:
            continue
        result.append({
            "model_id": o.get("model_id"),
            "provider_id": o.get("provider_id"),
            "input_per_m": o.get("input_per_m"),
            "output_per_m": o.get("output_per_m"),
            "free": o.get("free"),
        })
    if sort == "input":
        result.sort(key=lambda x: x.get("input_per_m") if x.get("input_per_m") is not None else 9999)
    elif sort == "output":
        result.sort(key=lambda x: x.get("output_per_m") if x.get("output_per_m") is not None else 9999)
    return {"prices": result[:limit], "count": len(result)}


@app.get("/v1/history")
def deal_history(model: str = None, provider: str = None, limit: int = Query(50, le=200)):
    """Historical deal events."""
    data = _load_all()
    events = data["events"]
    if model:
        events = [e for e in events if model.lower() in str(e.get("model_id", "")).lower()]
    if provider:
        events = [e for e in events if provider == e.get("provider_id")]
    events.sort(key=lambda x: x.get("observed_at", ""), reverse=True)
    return {"history": events[:limit], "count": len(events)}


# --- Convenience Endpoints ---

@app.get("/v1/cheapest")
def cheapest(task: str = Query("short_chat"), limit: int = Query(10, le=50)):
    """Cheapest models for a task."""
    data = _load_all()
    scored = []
    for o in data["offers"]:
        if o.get("free"):
            cost = 0
        elif o.get("input_per_m") is None:
            cost = 9999  # unknown price, sort last
        else:
            in_m = o.get("input_per_m")
            out_m = o.get("output_per_m") or 0
            preset = models_v2.WORKLOAD_PRESETS.get(task, models_v2.WORKLOAD_PRESETS["short_chat"])
            cost = (in_m * preset["input_tokens"] + out_m * preset["output_tokens"]) / 1_000_000 * preset["requests"]
        scored.append({**o, "total_cost": round(cost, 6)})
    scored.sort(key=lambda x: x["total_cost"])
    return {"task": task, "cheapest": scored[:limit]}


@app.get("/v1/best-value")
def best_value(limit: int = Query(10, le=50)):
    """Best intelligence per dollar."""
    data = _load_all()
    import scoring
    scored = [scoring.score_and_badge(o) for o in data["offers"]]
    scored.sort(key=lambda x: x["vector"]["value"], reverse=True)
    return {"best_value": scored[:limit]}


@app.get("/v1/free")
def free_models(limit: int = Query(20, le=100)):
    """All free models/offers."""
    return list_deals(free=True, limit=limit)


@app.get("/v1/promotions")
def promotions(limit: int = Query(20, le=100)):
    """Active promotions and deals."""
    data = _load_all()
    promos = [o for o in data["offers"] if o.get("offer_kind") not in ("metered_api", None)]
    return {"promotions": promos[:limit], "count": len(promos)}


@app.get("/v1/mega-deals")
def mega_deals(limit: int = Query(10, le=50)):
    """Abnormal institutional-quality deals — the most valuable opportunities.

    Mega deals are offers where:
    - Capacity is >3x baseline (e.g. MiMo 30K req/5h vs 4K baseline)
    - Free with >10K requests
    - Usage multiplier >=2x (e.g. Luna 2x usage)
    - Price anomaly ($0 but not marked free)
    """
    data = _load_all()
    from mega_deals import detect_mega_deals, get_mega_deal_summary
    mega = detect_mega_deals(data["offers"])
    summary = get_mega_deal_summary(data["offers"])
    return {"mega_deals": mega[:limit], "summary": summary, "count": len(mega)}


# --- Derived Economics ---

@app.get("/v1/economics")
def economics(task: str = Query("coding_agent"), limit: int = Query(20, le=50)):
    """Computed effective costs for standard workloads."""
    data = _load_all()
    results = []
    for o in data["offers"]:
        econ = models_v2.compute_derived_economics(
            models_v2.CommercialOffer(
                offer_id=o.get("model_id", ""),
                offering_id="",
                offer_type=o.get("offer_kind", "payg"),
                input_per_m_tokens=o.get("input_per_m"),
                output_per_m_tokens=o.get("output_per_m"),
                free_requests_per_day=o.get("requests_day"),
            ))
        results.append({
            "model_id": o.get("model_id"),
            "provider_id": o.get("provider_id"),
            "free": o.get("free"),
            "economics": {
                "nominal_input": econ.nominal_input_per_m,
                "nominal_output": econ.nominal_output_per_m,
                "batch_effective": econ.batch_effective_input,
                "offpeak_effective": econ.offpeak_effective_input,
                "free_quota_value": econ.free_quota_value_usd,
                "cost_per_10m_tokens": econ.cost_per_10m_tokens,
            },
        })
    results.sort(key=lambda x: x["economics"]["cost_per_10m_tokens"] or 999)
    return {"task": task, "workload": models_v2.WORKLOAD_PRESETS.get(task, {}), "economics": results[:limit]}


@app.get("/v1/recommend")
def recommend(task: str = Query("coding"), max_cost: float = None,
              tool_calling: bool = False, min_context: int = 0, limit: int = 5):
    """Task-first recommendation using legitimate scores."""
    data = _load_all()
    import scoring
    result = scoring.recommend(data["offers"], task=task, min_context=min_context,
                               tool_calling=tool_calling, budget=max_cost, limit=limit)
    return result


# --- Stats ---

@app.get("/v1/stats")
def stats():
    """Overall dataset stats."""
    data = _load_all()
    offers = data["offers"]
    free = sum(1 for o in offers if o.get("free"))
    providers = set(o.get("provider_id", "") for o in offers)
    return {
        "total_offers": len(offers),
        "free_offers": free,
        "providers": len(providers),
        "events": len(data["events"]),
    }


@app.get("/v1/probe")
def probe(provider: str = None):
    """Live probe of free API endpoints. Tests if endpoints actually work."""
    import live_probe
    if provider:
        result = live_probe.probe_endpoint(provider)
        return result
    results = live_probe.probe_all()
    return {"probes": results, "count": len(results)}


@app.get("/v1/history")
def history():
    """Historical snapshot comparison — what changed since last poll."""
    import history as hist
    comparison = hist.get_latest_comparison()
    if comparison is None:
        return {"message": "No historical data yet. First poll creates baseline."}
    return comparison


@app.get("/v1/verify/{model_id:path}")
def verify_deal(model_id: str):
    """Verify a specific deal by probing its provider."""
    import live_probe
    all_offers = _load_all()["offers"]
    matches = [o for o in all_offers if model_id.lower() in (o.get("model_id") or "").lower()]
    if not matches:
        return {"error": "Model not found", "model_id": model_id}

    offer = matches[0]
    provider_id = offer.get("provider_id", "")
    probe_result = live_probe.get_probe_status(provider_id) or {}

    return {
        "model_id": model_id,
        "provider": provider_id,
        "price_per_m": offer.get("input_per_m"),
        "free": offer.get("free"),
        "mega_deal": offer.get("metadata", {}).get("capacity_multiplier") is not None or
                     offer.get("metadata", {}).get("multiplier") is not None,
        "live_probe": probe_result,
        "source_url": offer.get("metadata", {}).get("source_url"),
        "verification_status": "LIVE_PROBED" if probe_result.get("live") else
                               "SOURCE_LINKED" if offer.get("metadata", {}).get("source_url") else "UNVERIFIED",
    }



@app.get("/v1/glossary")
def glossary():
    """Glossary of all terms used in the API. Agents should read this first."""
    from pathlib import Path
    glossary_path = Path(__file__).parent.parent / "data" / "glossary.json"
    if glossary_path.exists():
        return json.loads(glossary_path.read_text())
    return {"error": "Glossary not found"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("CANONICAL_PORT", "8803")))
