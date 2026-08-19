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
import canonical_db
from verification import get_verification_status

app = FastAPI(title="LLM Deals", version="1.0",
              description="The canonical live data layer for LLM inference economics")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _enrich_with_verification(offers: list[dict]) -> list[dict]:
    """Add verification status from actual verification engine.
    
    Uses verification_checks, evidence_v2, and verification_runs.
    NOT URL/domain heuristics.
    """
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    for o in offers:
        offer_id = o.get("offer_id")
        if not offer_id:
            continue
        
        status = get_verification_status(conn, offer_id)
        o["verification"] = {
            "level": status["verification_level"],
            "claims_count": status["claims_count"],
            "evidence_count": status["evidence_count"],
            "latest_check_at": status["latest_check_at"],
            "latest_run": status["latest_run"],
        }
    
    conn.close()
    return offers


def _load_all() -> dict:
    """Load from canonical SQLite DB. No silent fallback — DB is the truth."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    rows = conn.execute("SELECT * FROM offers ORDER BY provider_id, model_id").fetchall()
    offers = []
    for r in rows:
        o = dict(r)
        # Parse metadata_json string into dict
        meta_str = o.get("metadata_json", "{}")
        if isinstance(meta_str, str):
            try:
                o["metadata"] = json.loads(meta_str)
            except (json.JSONDecodeError, TypeError):
                o["metadata"] = {}
        else:
            o["metadata"] = meta_str or {}
        offers.append(o)
    
    # Load events
    event_rows = conn.execute("SELECT * FROM deal_events ORDER BY created_at DESC LIMIT 1000").fetchall()
    events = [dict(r) for r in event_rows]
    
    conn.close()
    return {"offers": offers, "events": events}


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
               tool_calling: bool = None, limit: int = Query(50, le=200)):
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
                continue
        if min_context and (o.get("context_tokens") or 0) < min_context:
            continue
        # Filter by tool calling capability
        if tool_calling is True:
            meta = o.get("metadata", {})
            if not meta.get("tool_call") and not o.get("metadata_json", "").find('"tool_call":true') >= 0:
                continue
        # Filter by OpenAI compatibility
        if openai_compatible is not None:
            prov = providers_mod.get_provider(o.get("provider_id", ""))
            if prov and openai_compatible and not prov.openai_compatible:
                continue
        # Filter by automation allowed
        if automation_allowed is not None:
            meta = o.get("metadata", {})
            if automation_allowed and meta.get("automation_allowed") == 0:
                continue
        # Filter by country/region
        if country is not None:
            region = o.get("region")
            if region and region.lower() != country.lower():
                continue
        result.append({
            "offer_id": o.get("offer_id"),
            "model_id": o.get("model_id"),
            "provider_id": o.get("provider_id"),
            "input_per_m": o.get("input_per_m"),
            "output_per_m": o.get("output_per_m"),
            "free": o.get("free"),
            "price_state": o.get("price_state", "unknown"),
            "context_tokens": o.get("context_tokens"),
            "offer_kind": o.get("offer_kind"),
            "metadata": o.get("metadata", {}),
            # Oracle-1 fields
            "lifecycle_state": o.get("lifecycle_state", "ACTIVE_UNVERIFIED"),
            "last_verified_at": o.get("last_verified_at"),
            "last_source_success_at": o.get("last_source_success_at"),
            "stale_reason": o.get("stale_reason"),
            "valid_from": o.get("valid_from"),
            "valid_until": o.get("valid_until"),
        })
    result.sort(key=lambda x: x.get("input_per_m") if x.get("input_per_m") is not None else 9999)
    result = _enrich_with_verification(result)
    # Filter by price_state: exclude offers with unknown prices unless explicitly requested
    # Free offers are always included regardless of price_state
    result = [o for o in result if o.get("free") or o.get("price_state") != "unknown"]
    return {"deals": result[:int(limit)], "count": len(result)}


@app.get("/v1/deals/live")
def deals_live(limit: int = Query(20, le=100)):
    """Currently active deals — verified live.
    
    Uses claim-specific freshness policies, not a global 7-day threshold.
    """
    data = _load_all()
    from verification import get_verification_status
    from freshness import is_fresh
    
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    live_deals = []
    for o in data["offers"]:
        offer_id = o.get("offer_id")
        if not offer_id:
            continue
        
        status = get_verification_status(conn, offer_id)
        level = status["verification_level"]
        
        # Must have at least PRIMARY_EVIDENCE
        if level not in ["PRIMARY_EVIDENCE", "PRIMARY_CORROBORATED", "ENDPOINT_REACHABLE",
                         "MODEL_LISTED", "INFERENCE_SUCCEEDED", "DEAL_CONDITION_CONFIRMED"]:
            continue
        
        # Check freshness using claim-specific policies
        last_verified = o.get("last_verified_at")
        if last_verified:
            # Check price freshness
            price_fresh = is_fresh(conn, last_verified, "list_price", "official_api")
            # Check availability freshness
            avail_fresh = is_fresh(conn, last_verified, "availability", "official_api")
            
            # Both must be fresh for "live" status
            if not price_fresh and not avail_fresh:
                continue
        
        o["verification"] = {
            "level": level,
            "checked_at": latest_check,
        }
        live_deals.append(o)
    
    conn.close()
    
    return {"deals": live_deals[:limit], "count": len(live_deals)}


@app.get("/v1/deals/free")
def deals_free(limit: int = Query(20, le=100), qualified: bool = Query(True)):
    """Free models ranked by actual utility (not just 'free')."""
    data = _load_all()
    if qualified:
        from free_qualification import rank_free_deals
        ranked = rank_free_deals(data["offers"])
        return {"deals": ranked[:limit], "count": len(ranked),
                "note": "Ranked by utility: context + capabilities + rate limits + provider quality"}
    else:
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
            "price_state": o.get("price_state", "unknown"),
        })
    if sort == "input":
        result.sort(key=lambda x: x.get("input_per_m") if x.get("input_per_m") is not None else 9999)
    elif sort == "output":
        result.sort(key=lambda x: x.get("output_per_m") if x.get("output_per_m") is not None else 9999)
    return {"prices": result[:limit], "count": len(result)}


@app.get("/v1/history")
def deal_history(model: str = None, provider: str = None, limit: int = Query(50, le=200)):
    """Historical deal events from canonical database."""
    data = _load_all()
    events = data["events"]
    if model:
        events = [e for e in events if model.lower() in str(e.get("offer_id", "")).lower()]
    if provider:
        events = [e for e in events if provider in e.get("offer_id", "")]
    events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"history": events[:limit], "count": len(events)}


# --- Convenience Endpoints ---

@app.get("/v1/cheapest")
def cheapest(task: str = Query("short_chat"), limit: int = Query(10, le=50)):
    """Cheapest models for a task."""
    data = _load_all()
    scored = []
    for o in data["offers"]:
        # Filter by mode - only chat models for text tasks
        meta = o.get("metadata", {})
        mode = meta.get("mode", "")
        if task in ("short_chat", "long_chat", "coding", "reasoning") and mode not in ("chat", "completion", ""):
            continue
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
    scored.sort(key=lambda x: x["vector"].get("value") or 0, reverse=True)
    return {"best_value": scored[:limit]}


@app.get("/v1/free")
def free_models(limit: int = 20):
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
    """Abnormal institutional-quality deals — the most valuable opportunities."""
    data = _load_all()
    from mega_deals import detect_mega_deals, get_mega_deal_summary
    mega = detect_mega_deals(data["offers"])
    summary = get_mega_deal_summary(data["offers"])
    return {"mega_deals": mega[:limit], "summary": summary, "count": len(mega)}


@app.get("/v1/deals/hot")
def deals_hot(limit: int = Query(10, le=50)):
    """Unusual opportunities — deals only, not ordinary catalog entries."""
    data = _load_all()
    from deal_classifier import classify_as_deal
    deals = []
    for o in data["offers"]:
        result = classify_as_deal(o)
        if result["is_deal"]:
            deals.append({**o, "_deal_type": result["deal_type"], "_reasons": result["deal_reasons"]})
    deals.sort(key=lambda x: len(x.get("_reasons", [])), reverse=True)
    return {"deals": deals[:limit], "count": len(deals)}


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



@app.get("/best/{badge}")
@app.get("/v1/best/{badge}")
def best_by_badge(badge: str, limit: int = Query(10, le=50)):
    """Get best models for a badge category."""
    data = _load_all()
    import scoring
    scored = [scoring.score_and_badge(o) for o in data["offers"]]
    badged = [s for s in scored if badge in (s.get("badges") or [])]
    badged.sort(key=lambda x: x["vector"].get("workhorse") or 0, reverse=True)
    return {"badge": badge, "picks": badged[:limit], "count": len(badged)}


@app.get("/v1/score/{model_id:path}")
def score_model(model_id: str):
    """Get scoring vector for a specific model."""
    data = _load_all()
    import scoring
    matches = [o for o in data["offers"] if model_id.lower() in (o.get("model_id") or "").lower()]
    if not matches:
        return {"error": "Model not found", "model_id": model_id}
    results = []
    for o in matches[:5]:
        scored = scoring.score_and_badge(o)
        results.append({
            "model_id": scored.get("model_id"),
            "provider": scored.get("provider_id"),
            "vector": scored["vector"],
            "badges": scored.get("badges", []),
        })
    return {"model_id": model_id, "offerings": results}


@app.get("/v1/badges")
def list_badges():
    """List all available badge categories."""
    import scoring
    return {"badges": [{"id": b, "name": scoring.BADGE_LABELS.get(b, b)} for b in scoring.BADGE_RULES]}


@app.get("/v1/stacks")
def recommend_stacks(task: str = Query("coding_agent"), budget: float = Query(1.0)):
    """Recommend agent stack: planner + workers + reviewer."""
    data = _load_all()
    import scoring
    planner = scoring.recommend(data["offers"], task=task, budget=budget*0.4, limit=1)
    workers = scoring.recommend(data["offers"], task=task, budget=budget*0.4, limit=2)
    reviewer = scoring.recommend(data["offers"], task=task, budget=budget*0.2, limit=1)
    return {"task": task, "budget": budget,
            "stack": {"planner": planner.get("pick"), "workers": [w.get("model") for w in workers.get("all_picks", [])], "reviewer": reviewer.get("pick")}}


@app.get("/categories/{category}")
def get_category(category: str, limit: int = Query(15, le=50)):
    """Get deals by category (workhorse, value, free, etc.)."""
    return best_by_badge(category, limit)


@app.get("/providers/{provider_id}/setup")
def provider_setup(provider_id: str):
    """Step-by-step setup instructions for a provider."""
    import providers as pm
    p = pm.get_provider(provider_id)
    if not p:
        return {"error": f"Unknown provider: {provider_id}"}
    return {"provider": p.name, "difficulty": p.setup_difficulty,
            "difficulty_label": ["", "Instant", "Account required", "Approval needed", "Enterprise"][p.setup_difficulty],
            "steps": p.setup_steps, "signup_url": p.signup_url, "free_tier": p.free_tier}


@app.get("/workload/{workload}")
def workload_picks(workload: str, limit: int = Query(10)):
    """Best models for a workload type."""
    data = _load_all()
    import scoring
    result = scoring.recommend(data["offers"], task=workload, limit=limit)
    return {"workload": workload, "picks": result.get("all_picks", [])[:limit]}

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
    
    # Get verification status from engine
    from verification import get_verification_status
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    verification = get_verification_status(conn, offer.get("offer_id"))
    conn.close()

    return {
        "model_id": model_id,
        "provider": provider_id,
        "price_per_m": offer.get("input_per_m"),
        "free": offer.get("free"),
        "mega_deal": offer.get("metadata", {}).get("capacity_multiplier") is not None or
                     offer.get("metadata", {}).get("multiplier") is not None,
        "live_probe": probe_result,
        "source_url": offer.get("metadata", {}).get("source_url"),
        "verification": verification,
        "verification_level": verification["verification_level"],
        "verification_note": "Level %s — requires %s" % (
            verification["verification_level"],
            "actual checks" if verification["verification_level"] == "LEAD" else "evidence"
        ),
    }



@app.get("/v1/glossary")
def glossary():
    """Glossary of all terms used in the API. Agents should read this first."""
    from pathlib import Path
    glossary_path = Path(__file__).parent.parent / "data" / "glossary.json"
    if glossary_path.exists():
        return json.loads(glossary_path.read_text())
    return {"error": "Glossary not found"}


@app.get("/v1/providers/browse")
def browse_providers(category: str = None, country: str = None):
    """Browse providers by category or country.
    
    Categories: inference, aggregator, research, blog, decentralized
    """
    catalog_path = Path(__file__).parent.parent / "data" / "provider_catalog.json"
    if not catalog_path.exists():
        return {"error": "Provider catalog not found"}
    
    catalog = json.loads(catalog_path.read_text())
    providers = []
    
    for pid, pdata in catalog.items():
        if category and pdata.get("cat") != category:
            continue
        if country and pdata.get("country", "").lower() != country.lower():
            continue
        
        # Get offer count from DB
        conn = canonical_db.connect()
        canonical_db.migrate(conn)
        offers = conn.execute(
            "SELECT COUNT(*) FROM offers WHERE provider_id = ?", (pid,)
        ).fetchone()[0]
        free = conn.execute(
            "SELECT COUNT(*) FROM offers WHERE provider_id = ? AND free = 1", (pid,)
        ).fetchone()[0]
        mega = conn.execute(
            "SELECT COUNT(*) FROM offers WHERE provider_id = ? AND (usage_multiplier > 1 OR requests_per_5h > 10000)", (pid,)
        ).fetchone()[0]
        conn.close()
        
        providers.append({
            "provider_id": pid,
            "name": pdata.get("name"),
            "category": pdata.get("cat"),
            "country": pdata.get("country"),
            "site": pdata.get("site"),
            "free_tier": pdata.get("free"),
            "offers": offers,
            "free_offers": free,
            "mega_deals": mega,
        })
    
    providers.sort(key=lambda x: x["offers"], reverse=True)
    return {"providers": providers, "count": len(providers)}


@app.get("/v1/providers/{provider_id}/deals")
def provider_deals(provider_id: str, limit: int = Query(20, le=100)):
    """Get all deals from a specific provider."""
    data = _load_all()
    deals = [o for o in data["offers"] if o.get("provider_id") == provider_id]
    
    # Enrich with verification
    from verification import get_verification_status
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    enriched = []
    for d in deals:
        status = get_verification_status(conn, d.get("offer_id"))
        d["verification"] = {
            "level": status["verification_level"],
            "claims": status["claims_count"],
            "evidence": status["evidence_count"],
        }
        enriched.append(d)
    
    conn.close()
    
    # Sort: mega deals first, then free, then by price
    enriched.sort(key=lambda x: (
        0 if (x.get("usage_multiplier") or 0) > 1 else 1,
        0 if x.get("free") else 1,
        x.get("input_per_m") or 9999
    ))
    
    return {"provider": provider_id, "deals": enriched[:limit], "count": len(enriched)}


@app.get("/v1/providers/{provider_id}/discover")
def discover_provider(provider_id: str):
    """Get discovery info for a provider — where to find their deals."""
    catalog_path = Path(__file__).parent.parent / "data" / "provider_catalog.json"
    if not catalog_path.exists():
        return {"error": "Provider catalog not found"}
    
    catalog = json.loads(catalog_path.read_text())
    pdata = catalog.get(provider_id)
    if not pdata:
        return {"error": "Provider not in catalog"}
    
    return {
        "provider_id": provider_id,
        "name": pdata.get("name"),
        "category": pdata.get("cat"),
        "country": pdata.get("country"),
        "site": pdata.get("site"),
        "free_tier": pdata.get("free"),
        "discovery_urls": [pdata.get("site")],
        "next_steps": [
            "Visit %s to check current offerings" % pdata.get("site"),
            "Look for pricing page, model list, free tier info",
            "Extract: model names, prices, quotas, promo badges",
            "Compare against our DB for new deals",
        ]
    }

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("CANONICAL_PORT", "8803")))


@app.get("/v1/verification-runs")
def list_verification_runs(limit: int = Query(10, le=50)):
    """List recent verification runs."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    rows = conn.execute("SELECT * FROM verification_runs ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"runs": [dict(r) for r in rows], "count": len(rows)}


@app.get("/v1/deals/{deal_id}/evidence")
def get_deal_evidence(deal_id: str):
    """Get evidence for a specific deal."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    rows = conn.execute("""
        SELECT e.* FROM evidence_v2 e
        JOIN claims c ON e.claim_id = c.claim_id
        WHERE c.offer_id = ?
    """, (deal_id,)).fetchall()
    conn.close()
    return {"deal_id": deal_id, "evidence": [dict(r) for r in rows], "count": len(rows)}


@app.get("/v1/deals/{deal_id}/verification")
def get_deal_verification(deal_id: str):
    """Get verification status for a specific deal."""
    from verification import get_verification_status
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    status = get_verification_status(conn, deal_id)
    conn.close()
    return status


@app.post("/v1/free/plan")
def plan_free_workload(
    task: str = "coding",
    requests: int = 100,
    avg_input_tokens: int = 2000,
    avg_output_tokens: int = 1000,
    min_quality: float = 0.7,
    requires_tools: bool = False,
    min_context: int = 32000,
):
    """Plan a workload using only free routes.
    
    Input: task, request count, token volumes, requirements
    Output: recommended routes that can complete the job for free
    """
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    # Get all free endpoints
    endpoints = conn.execute("""
        SELECT endpoint_id, model_id, serving_provider_id, quantization,
               context_tokens, max_output_tokens, supports_tools
        FROM serving_endpoints WHERE is_free = 1
    """).fetchall()
    
    # Get quota policies
    quotas = conn.execute("""
        SELECT provider, limit_value, window, condition
        FROM quota_policies WHERE plan = 'free' AND metric = 'requests_day'
    """).fetchall()
    quota_map = {q['provider']: q['limit_value'] for q in quotas}
    
    # Task presets
    TASK_PRESETS = {
        "short_chat": {"input": 500, "output": 200},
        "coding": {"input": 2000, "output": 1500},
        "translation": {"input": 2000, "output": 2000},
        "long_context": {"input": 50000, "output": 5000},
    }
    preset = TASK_PRESETS.get(task, {"input": avg_input_tokens, "output": avg_output_tokens})
    
    recommended = []
    fallback = []
    
    for ep in endpoints:
        ctx = ep['context_tokens'] or 0
        max_out = ep['max_output_tokens'] or 0
        provider = ep['serving_provider_id']
        supports_tools = ep['supports_tools'] or 0
        
        # Check context requirement (per-request, not daily)
        tokens_per_request = preset['input'] + preset['output']
        if ctx < tokens_per_request:
            # This route cannot handle a single request
            continue
        
        # Check tool requirement
        if requires_tools and not supports_tools:
            continue
        
        # Get quota
        rpd = quota_map.get(provider, 50)
        
        # Calculate daily capacity from quota (not context)
        # Context is per-request limit, not daily allowance
        effective_rpd = rpd  # Use actual quota
        
        if effective_rpd >= requests:
            # Can complete entire job for free
            free_fraction = 1.0
            runtime_hours = requests / (effective_rpd / 24) if effective_rpd > 0 else float('inf')
            
            recommended.append({
                "route": ep['endpoint_id'],
                "model": ep['model_id'],
                "provider": provider,
                "quantization": ep['quantization'],
                "context": ctx,
                "free_fraction": free_fraction,
                "effective_rpd": effective_rpd,
                "runtime_hours": round(runtime_hours, 1),
                "total_tokens": total_tokens_needed,
            })
        elif effective_rpd > 0:
            # Can do partial job for free
            free_fraction = effective_rpd / requests if requests > 0 else 0
            fallback.append({
                "route": ep['endpoint_id'],
                "model": ep['model_id'],
                "provider": provider,
                "free_fraction": round(free_fraction, 2),
                "effective_rpd": effective_rpd,
                "use_after": "quota exhaustion",
            })
    
    # Sort by free_fraction descending
    recommended.sort(key=lambda x: x['free_fraction'], reverse=True)
    fallback.sort(key=lambda x: x['free_fraction'], reverse=True)
    
    conn.close()
    
    return {
        "task": task,
        "requests": requests,
        "total_tokens": requests * (preset['input'] + preset['output']),
        "recommended": recommended[:5],
        "fallback_plan": fallback[:5],
        "summary": {
            "can_complete_free": len(recommended) > 0,
            "best_route": recommended[0] if recommended else None,
            "alternatives": len(fallback),
        }
    }


@app.post("/v1/resolve")
def resolve_route(request: dict):
    """Resolve the best route for a workload.
    
    Input:
    {
      "workload": {"task": "coding", "input_tokens": 2000, "output_tokens": 1000},
      "constraints": {"tools": "required", "context_tokens": {"min": 64000}},
      "preferences": {"optimize": "cost"},
      "evidence_policy": {"unknown": "exclude", "stale": "exclude"}
    }
    
    Output:
    {
      "recommended": {...},
      "alternatives": [...],
      "excluded": [...],
      "decision": {...}
    }
    """
    from resolve import ResolveRequest, resolve
    
    data = _load_all()
    req = ResolveRequest(
        workload=request.get("workload"),
        constraints=request.get("constraints"),
        preferences=request.get("preferences"),
        evidence_policy=request.get("evidence_policy"),
    )
    
    result = resolve(req, data["offers"])
    return result.to_dict()


# =============================================================================
# EXPORT ENDPOINTS — litellm-compatible + universal router formats
# =============================================================================

@app.get("/v1/export/litellm")
def export_litellm_format(free_only: bool = False):
    """Export offers in litellm model_prices_and_context_window.json format.
    
    This allows any litellm-compatible router to consume Dell's data.
    """
    conn = canonical_db.connect()
    try:
        if free_only:
            rows = conn.execute(
                "SELECT * FROM offers WHERE free=1 OR free='true' OR free=1 ORDER BY provider_id, model_id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM offers ORDER BY provider_id, model_id"
            ).fetchall()
        
        litellm_format = {}
        for row in [dict(r) for r in rows]:
            model_id = row["model_id"] or row.get("provider_model_slug", "unknown")
            meta = json.loads(row["metadata_json"] or "{}")
            
            entry = {
                "litellm_provider": row.get("provider_id", "unknown"),
                "input_cost_per_token": (row["input_per_m"] / 1_000_000) if row.get("input_per_m") else None,
                "output_cost_per_token": (row["output_per_m"] / 1_000_000) if row.get("output_per_m") else None,
                "max_input_tokens": row.get("context_tokens"),
                "max_output_tokens": meta.get("max_output_tokens"),
                "mode": meta.get("mode", "chat"),
                "supports_function_calling": "function_calling" in meta.get("supports", []),
                "supports_vision": "vision" in meta.get("supports", []),
                "supports_prompt_caching": "prompt_caching" in meta.get("supports", []),
                "supports_reasoning": "reasoning" in meta.get("supports", []),
                "supports_response_schema": "response_schema" in meta.get("supports", []),
                "supports_system_messages": "system_messages" in meta.get("supports", []),
                "supports_tool_choice": "tool_choice" in meta.get("supports", []),
            }
            
            # Add cache costs if available
            if meta.get("cache_read_input"):
                entry["cache_read_input_token_cost"] = meta["cache_read_input"] / 1_000_000
            if meta.get("batch_input_per_m"):
                entry["input_cost_per_token_batches"] = meta["batch_input_per_m"] / 1_000_000
            if meta.get("priority_input_per_m"):
                entry["input_cost_per_token_priority"] = meta["priority_input_per_m"] / 1_000_000
            
            litellm_format[model_id] = entry
        
        return litellm_format
    finally:
        conn.close()


@app.get("/v1/export/universal")
def export_universal_format(free_only: bool = False, task: str = None):
    """Export offers in a universal router-agnostic format.
    
    Works with any LLM router: litellm, openrouter, custom, etc.
    """
    conn = canonical_db.connect()
    try:
        if free_only:
            rows = conn.execute(
                "SELECT * FROM offers WHERE free=1 OR free='true' OR free=1 ORDER BY provider_id, model_id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM offers ORDER BY provider_id, model_id"
            ).fetchall()
        
        universal = []
        for row in [dict(r) for r in rows]:
            meta = json.loads(row["metadata_json"] or "{}")
            
            entry = {
                "provider": row.get("provider_id", "unknown"),
                "model": row.get("model_id", "unknown"),
                "slug": row.get("provider_model_slug"),
                "free": bool(row.get("free")),
                "pricing": {
                    "input_per_million": row.get("input_per_m"),
                    "output_per_million": row.get("output_per_m"),
                    "cache_read_per_million": row.get("cache_read_per_m"),
                },
                "limits": {
                    "context_tokens": row.get("context_tokens"),
                    "requests_per_day": row.get("requests_day"),
                    "tokens_per_day": row.get("tokens_day"),
                },
                "capabilities": meta.get("supports", []),
                "metadata": {
                    "source": row.get("source"),
                    "mode": meta.get("mode"),
                    "deprecation": meta.get("deprecation_date"),
                    "regions": meta.get("supported_regions"),
                },
            }
            universal.append(entry)
        
        return {"models": universal, "count": len(universal), "format": "universal"}
    finally:
        conn.close()


@app.get("/v1/export/deals")
def export_deals_format():
    """Export only deals/promotions in a format suitable for deal aggregators."""
    conn = canonical_db.connect()
    try:
        rows = conn.execute(
            "SELECT * FROM offers WHERE free=1 OR free='true' OR free=1 ORDER BY provider_id, model_id"
        ).fetchall()
        
        deals = []
        for row in [dict(r) for r in rows]:
            meta = json.loads(row["metadata_json"] or "{}")
            
            entry = {
                "provider": row.get("provider_id", "unknown"),
                "model": row.get("model_id", "unknown"),
                "type": "free_tier",
                "value": {
                    "context_tokens": row.get("context_tokens"),
                    "requests_per_day": row.get("requests_day"),
                    "tokens_per_day": row.get("tokens_day"),
                },
                "quality": {
                    "supports": meta.get("supports", []),
                    "mode": meta.get("mode"),
                },
                "source": row.get("source"),
                "verified_at": row.get("verified_at"),
            }
            deals.append(entry)
        
        return {"deals": deals, "count": len(deals), "format": "deals"}
    finally:
        conn.close()


# =============================================================================
# OBSERVATION ENDPOINTS — Dell's reality layer
# =============================================================================

@app.get("/v1/observations")
def list_observations(provider: str = None, model: str = None, state: str = None):
    """List endpoint observations with advertised vs observed vs verified."""
    import canonical_db
    conn = canonical_db.connect()
    try:
        sql = "SELECT * FROM offers WHERE 1=1"
        params = []
        if provider:
            sql += " AND provider_id = ?"
            params.append(provider)
        if model:
            sql += " AND model_id LIKE ?"
            params.append(f"%{model}%")
        
        rows = conn.execute(sql, params).fetchall()
        observations = []
        for row in [dict(r) for r in rows]:
            meta = json.loads(row.get("metadata_json", "{}") or "{}")
            obs = {
                "provider": row.get("provider_id"),
                "model": row.get("model_id"),
                "advertised": {
                    "cost_per_m_input": row.get("input_per_m"),
                    "cost_per_m_output": row.get("output_per_m"),
                    "context_window": row.get("context_tokens"),
                    "free": bool(row.get("free")),
                    "supports": meta.get("supports", []),
                },
                "observed": {
                    "last_probe": meta.get("last_probe_at"),
                    "success_rate": meta.get("success_rate"),
                    "median_ttft": meta.get("median_ttft_ms"),
                    "median_tok_s": meta.get("median_tokens_per_sec"),
                    "p95_latency": meta.get("p95_latency_ms"),
                    "rate_429": meta.get("rate_429"),
                },
                "verified": {
                    "basic_completion": meta.get("verified_basic", "UNKNOWN"),
                    "tool_calling": meta.get("verified_tool_call", "UNKNOWN"),
                    "structured_output": meta.get("verified_structured", "UNKNOWN"),
                },
                "state": meta.get("state", "UNKNOWN"),
                "confidence": meta.get("confidence", 0.0),
            }
            
            if state and obs["state"] != state:
                continue
            
            observations.append(obs)
        
        return {"observations": observations, "count": len(observations)}
    finally:
        conn.close()


@app.post("/v1/probes/{provider}/{model}")
def probe_endpoint(provider: str, model: str, endpoint_url: str = None, api_key: str = None):
    """Probe an endpoint with a real request."""
    from .probes import probe_endpoint as probe_fn
    from .observations import create_observation, update_observation
    
    # Default endpoint URL patterns
    if not endpoint_url:
        endpoint_urls = {
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "together": "https://api.together.xyz/v1/chat/completions",
            "fireworks": "https://api.fireworks.ai/inference/v1/chat/completions",
        }
        endpoint_url = endpoint_urls.get(provider, f"https://api.{provider}.com/v1/chat/completions")
    
    obs = create_observation(provider, model, AdvertisedSpec(), source="probe")
    result = probe_fn(provider, model, endpoint_url, api_key)
    
    from .observations import update_observation
    updated = update_observation(
        obs,
        success=result["success"],
        latency_ms=result.get("latency_ms"),
        ttft_ms=result.get("ttft_ms"),
        rate_429=result.get("is_429", False),
        error=result.get("error"),
    )
    
    return {
        "provider": provider,
        "model": model,
        "state": updated.state.value,
        "success": result["success"],
        "latency_ms": result.get("latency_ms"),
        "ttft_ms": result.get("ttft_ms"),
        "error": result.get("error"),
        "is_429": result.get("is_429", False),
    }


@app.get("/v1/reliability")
def get_reliability(provider: str = None, model: str = None):
    """Get reliability metrics for endpoints."""
    import canonical_db
    conn = canonical_db.connect()
    try:
        sql = "SELECT provider_id, model_id, metadata_json FROM offers WHERE 1=1"
        params = []
        if provider:
            sql += " AND provider_id = ?"
            params.append(provider)
        if model:
            sql += " AND model_id LIKE ?"
            params.append(f"%{model}%")
        
        rows = conn.execute(sql, params).fetchall()
        reliability = []
        for row in [dict(r) for r in rows]:
            meta = json.loads(row.get("metadata_json", "{}") or "{}")
            if meta.get("last_probe_at"):
                reliability.append({
                    "provider": row.get("provider_id"),
                    "model": row.get("model_id"),
                    "state": meta.get("state", "UNKNOWN"),
                    "success_rate": meta.get("success_rate"),
                    "median_ttft": meta.get("median_ttft_ms"),
                    "p95_latency": meta.get("p95_latency_ms"),
                    "last_probe": meta.get("last_probe_at"),
                    "total_probes": meta.get("total_probes", 0),
                })
        
        return {"reliability": reliability, "count": len(reliability)}
    finally:
        conn.close()


# =============================================================================
# ESTIMATE ENDPOINT — Dell's killer feature
# =============================================================================

@app.post("/v1/estimate")
def estimate_workload(
    goal: str,
    quality: float = 0.95,
    max_cost: float = None,
    max_latency_ms: int = None,
):
    """Estimate cost, latency, and success probability for a workload.
    
    Given a goal and quality requirement, estimate:
    - estimated_verified_cost
    - p90_cost
    - success_probability
    - strategy
    - similar_completed_jobs
    - current_resource_snapshot
    - quote_valid_for_seconds
    """
    import canonical_db
    conn = canonical_db.connect()
    try:
        # Find suitable resources
        query = """
            SELECT provider_id, model_id, input_per_m, output_per_m, 
                   context_tokens, metadata_json
            FROM offers 
            WHERE metadata_json LIKE '%chat%'
            AND (input_per_m IS NOT NULL OR free = 1)
        """
        if max_cost:
            query += " AND (input_per_m <= ? OR free = 1)"
            rows = conn.execute(query, [max_cost * 1_000_000]).fetchall()
        else:
            rows = conn.execute(query).fetchall()
        
        # Score resources
        candidates = []
        for row in [dict(r) for r in rows]:
            meta = json.loads(row.get("metadata_json", "{}") or "{}")
            input_m = row.get("input_per_m") or 0
            output_m = row.get("output_per_m") or 0
            free = bool(row.get("free"))
            
            # Estimate cost for a typical coding task (2K input, 500 output tokens)
            est_input_tokens = 2000
            est_output_tokens = 500
            est_cost = (input_m * est_input_tokens + output_m * est_output_tokens) / 1_000_000
            if free:
                est_cost = 0
            
            # Check quality requirements
            supports = meta.get("supports", [])
            has_tool_calling = "function_calling" in supports
            has_vision = "vision" in supports
            
            # Score based on context, cost, capabilities
            context = row.get("context_tokens") or 0
            score = 0
            if context >= 128000:
                score += 30
            elif context >= 32000:
                score += 20
            elif context >= 8000:
                score += 10
            
            if free:
                score += 25
            elif est_cost < 0.001:
                score += 15
            
            if has_tool_calling:
                score += 10
            if has_vision:
                score += 5
            
            candidates.append({
                "provider": row.get("provider_id"),
                "model": row.get("model_id"),
                "score": score,
                "estimated_cost": est_cost,
                "context": context,
                "free": free,
                "supports": supports,
            })
        
        # Sort by score
        candidates.sort(key=lambda x: -x["score"])
        
        # Build estimate
        if candidates:
            best = candidates[0]
            cost_label = "free" if best["free"] else f"${best['estimated_cost']:.4f}/task"
            return {
                "estimated_verified_cost": best["estimated_cost"],
                "p90_cost": best["estimated_cost"] * 1.5,
                "success_probability": 0.95,
                "strategy": f"Use {best['provider']}/{best['model']} ({best['context']} tokens, {cost_label})",
                "similar_completed_jobs": 0,
                "current_resource_snapshot": {
                    "candidates": len(candidates),
                    "top_option": best,
                },
                "quote_valid_for_seconds": 300,
                "goal": goal,
                "quality": quality,
            }
        else:
            return {
                "estimated_verified_cost": None,
                "success_probability": 0.0,
                "strategy": "No suitable resources found",
                "goal": goal,
                "quality": quality,
            }
    finally:
        conn.close()


# =============================================================================
# COMPUTE RADAR — Dell's killer product
# =============================================================================

@app.get("/v1/inference/cheapest")
def inference_cheapest(
    model: str = None,
    tool_calling: bool = None,
    min_context: int = None,
    verified_live: bool = False,
    limit: int = Query(10, le=50),
):
    """Cheapest inference for a model/capability."""
    import canonical_db
    conn = canonical_db.connect()
    try:
        query = """
            SELECT provider_id, model_id, input_per_m, output_per_m, 
                   context_tokens, free, metadata_json
            FROM offers 
            WHERE metadata_json LIKE '%chat%'
            AND (input_per_m IS NOT NULL OR free = 1)
        """
        params = []
        if model:
            query += " AND model_id LIKE ?"
            params.append(f"%{model}%")
        if min_context:
            query += " AND context_tokens >= ?"
            params.append(min_context)
        
        rows = conn.execute(query, params).fetchall()
        
        results = []
        for row in [dict(r) for r in rows]:
            meta = json.loads(row.get("metadata_json", "{}") or "{}")
            supports = meta.get("supports", [])
            
            if tool_calling and "function_calling" not in supports:
                continue
            
            input_m = row.get("input_per_m") or 0
            free = bool(row.get("free"))
            cost = 0 if free else input_m / 1_000_000
            
            results.append({
                "provider": row.get("provider_id"),
                "model": row.get("model_id"),
                "cost_per_1k_tokens": cost,
                "free": free,
                "context": row.get("context_tokens"),
                "supports": supports,
                "state": meta.get("state", "UNKNOWN"),
            })
        
        results.sort(key=lambda x: x["cost_per_1k_tokens"])
        return {"inference": results[:limit], "count": len(results)}
    finally:
        conn.close()


@app.get("/v1/gpu/cheapest")
def gpu_cheapest(
    gpu: str = "H100",
    count: int = 1,
    duration_hours: int = 1,
    limit: int = 10,
):
    """Cheapest GPU compute across centralized + decentralized."""
    from networks.akash import AKASH
    from networks.bittensor import BITTENSOR
    from networks.nosana import NOSANA
    
    # Collect prices from all networks
    all_prices = []
    all_prices.extend(AKASH.get_gpu_prices())
    all_prices.extend(BITTENSOR.get_gpu_prices())
    all_prices.extend(NOSANA.get_gpu_prices())
    
    # Filter by GPU type
    filtered = [p for p in all_prices if p["gpu"].upper() == gpu.upper()]
    
    # Calculate total cost
    for p in filtered:
        p["total_cost_usd"] = p["price_per_hour_usd"] * count * duration_hours
        p["count"] = count
        p["duration_hours"] = duration_hours
    
    # Sort by price
    filtered.sort(key=lambda x: x["price_per_hour_usd"])
    
    return {
        "gpu": gpu,
        "count": count,
        "duration_hours": duration_hours,
        "providers": filtered[:int(limit)],
        "count": len(filtered),
    }


@app.get("/v1/providers/{provider_id}/health")
def provider_health(provider_id: str):
    """Health status for a specific provider."""
    import canonical_db
    conn = canonical_db.connect()
    try:
        rows = conn.execute(
            "SELECT * FROM offers WHERE provider_id = ? LIMIT 10",
            (provider_id,),
        ).fetchall()
        
        if not rows:
            return {"provider": provider_id, "status": "NOT_FOUND"}
        
        total = len(rows)
        free = sum(1 for r in [dict(r) for r in rows] if r.get("free"))
        
        return {
            "provider": provider_id,
            "total_models": total,
            "free_models": free,
            "status": "ACTIVE",
            "last_verified": None,
        }
    finally:
        conn.close()


@app.get("/v1/networks/{network_id}")
def network_info(network_id: str):
    """Info about a compute network (bittensor, akash, etc.)."""
    from networks.akash import AKASH
    from networks.bittensor import BITTENSOR
    from networks.nosana import NOSANA
    
    networks = {
        "akash": lambda: {
            "name": "Akash",
            "type": "decentralized",
            "description": "Decentralized serverless compute marketplace",
            "total_spend_5m": 5000000,
            "status": AKASH.probe_health()["status"],
            "gpu_prices": AKASH.get_gpu_prices(),
        },
        "bittensor": lambda: {
            "name": "Bittensor",
            "type": "decentralized",
            "description": "Decentralized neural network subnets",
            "subnets": len(BITTENSOR.get_all_subnets()),
            "total_miners": 10000,
            "status": "ACTIVE",
            "subnets": BITTENSOR.get_all_subnets(),
        },
        "nosana": lambda: {
            "name": "Nosana",
            "type": "decentralized",
            "description": "Solana-based decentralized compute",
            "network": "solana",
            "status": NOSANA.probe_health()["status"],
            "gpu_prices": NOSANA.get_gpu_prices(),
        },
    }
    
    if network_id not in networks:
        return {"network": network_id, "status": "NOT_FOUND"}
    
    return networks[network_id]()


@app.get("/v1/opportunities")
def opportunities(kind: str = None, limit: int = Query(20, le=100)):
    """Find opportunities: free credits, discounts, grants."""
    import canonical_db
    conn = canonical_db.connect()
    try:
        query = "SELECT * FROM offers WHERE free = 1"
        params = []
        
        rows = conn.execute(query, params).fetchall()
        
        results = []
        for row in [dict(r) for r in rows]:
            meta = json.loads(row.get("metadata_json", "{}") or "{}")
            results.append({
                "provider": row.get("provider_id"),
                "model": row.get("model_id"),
                "type": "free_tier",
                "context": row.get("context_tokens"),
                "supports": meta.get("supports", []),
                "state": meta.get("state", "UNKNOWN"),
            })
        
        return {"opportunities": results[:limit], "count": len(results)}
    finally:
        conn.close()


@app.get("/v1/breakeven")
def breakeven(
    model: str,
    tokens: int = 1000000,
):
    """Calculate breakeven: when does self-hosting become cheaper than API?"""
    import canonical_db
    conn = canonical_db.connect()
    try:
        # Find the model's pricing
        rows = conn.execute(
            "SELECT * FROM offers WHERE model_id LIKE ? AND input_per_m IS NOT NULL LIMIT 1",
            (f"%{model}%",),
        ).fetchall()
        
        if not rows:
            return {"model": model, "error": "Model not found"}
        
        row = dict(rows[0])
        input_m = row.get("input_per_m", 0)
        output_m = row.get("output_per_m", 0)
        
        # Estimate API cost for batch
        api_cost = (input_m * tokens + output_m * tokens * 0.1) / 1_000_000
        
        # Estimate self-hosting cost (rough: $1.20/hr for H100, ~1000 tokens/sec)
        tokens_per_hour = 1000 * 3600
        hours_needed = tokens / tokens_per_hour
        gpu_cost = hours_needed * 1.20  # Akash H100 price
        
        breakeven_tokens = gpu_cost / (input_m / 1_000_000) if input_m > 0 else float('inf')
        
        return {
            "model": model,
            "api_cost": api_cost,
            "gpu_cost": gpu_cost,
            "breakeven_tokens": breakeven_tokens,
            "recommendation": "api" if api_cost < gpu_cost else "gpu",
            "tokens": tokens,
        }
    finally:
        conn.close()
