#!/usr/bin/env python3
"""app/api_v2.py — Deal Radar V2 API.

New endpoints for promotion intelligence:
  /deals/hot          — hottest deals right now
  /deals/free         — currently free offers
  /deals/expiring     — offers expiring soon
  /deals/changes      — recent price/promo changes
  /deals/workhorses   — best value for workload types
  /sources/health     — source health status
  /events             — recent promotion events
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

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware

import deal_score
import workloads
import source_health
import categories
import providers as providers_mod
import expiry
from sources import registry

app = FastAPI(title="Deal Radar V2", version="2.0",
              description="LLM inference deal intelligence — Slickdeals for AI compute")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _load_snapshot_data() -> dict:
    """Load the latest snapshot data from all sources."""
    snapshots_dir = ROOT / "snapshots"
    all_offers = []
    if snapshots_dir.exists():
        for f in snapshots_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                offers = data.get("offers", [])
                all_offers.extend(offers)
            except Exception:
                continue
    return {"offers": all_offers, "count": len(all_offers)}


def _load_events() -> list[dict]:
    """Load recent events from the events directory."""
    events_dir = ROOT / "events"
    events = []
    if events_dir.exists():
        for f in sorted(events_dir.glob("*.json"), reverse=True)[:10]:
            try:
                events.extend(json.loads(f.read_text()))
            except Exception:
                continue
    return events


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0", "timestamp": time.time()}


@app.get("/deals/hot")
def deals_hot(limit: int = Query(20, le=50)):
    """Hottest deals right now, scored by deal_score with expiry tracking."""
    data = _load_snapshot_data()
    offers = data["offers"]
    if not offers:
        return {"deals": [], "count": 0, "note": "No data yet — run discovery first"}
    baseline = deal_score.calculate_market_baseline(offers)
    scored = deal_score.score_deals(offers, baseline)
    # Add expiry tracking
    scored = expiry.enrich_offers_with_expiry(scored)
    scored.sort(key=lambda x: x.get("deal_score", 0), reverse=True)
    return {"deals": scored[:limit], "count": len(scored), "timestamp": time.time()}


@app.get("/deals/free")
def deals_free(limit: int = Query(20, le=50)):
    """Currently free offers."""
    data = _load_snapshot_data()
    free = [o for o in data["offers"] if o.get("free")]
    return {"deals": free[:limit], "count": len(free), "timestamp": time.time()}


@app.get("/deals/expiring")
def deals_expiring(hours: int = Query(24, le=168), limit: int = Query(20, le=50)):
    """Offers expiring within N hours with precise countdown."""
    data = _load_snapshot_data()
    all_offers = data["offers"]
    enriched = expiry.enrich_offers_with_expiry(all_offers)

    # Filter by hours
    expiring = []
    for o in enriched:
        exp = o.get("expiry", {})
        h = exp.get("hours_remaining")
        if h is not None and 0 < h <= hours:
            o["countdown"] = expiry.format_countdown(h)
            o["expires_at"] = exp.get("expires_at")
            expiring.append(o)

    expiring.sort(key=lambda x: x.get("expiry", {}).get("hours_remaining") or 9999)
    return {"deals": expiring[:limit], "count": len(expiring), "hours_window": hours,
            "timestamp": time.time()}


@app.get("/deals/expired")
def deals_expired(limit: int = Query(20, le=50)):
    """Recently expired deals — for tracking what ended."""
    data = _load_snapshot_data()
    all_offers = data["offers"]
    enriched = expiry.enrich_offers_with_expiry(all_offers)
    expired = [o for o in enriched if o.get("expiry", {}).get("status") == "expired"]
    return {"deals": expired[:limit], "count": len(expired), "timestamp": time.time()}


@app.get("/deals/changes")
def deals_changes():
    """Recent price/promo changes."""
    events = _load_events()
    return {"events": events[:50], "count": len(events), "timestamp": time.time()}


@app.get("/deals/workhorses")
def deals_workhorses(workload: str = Query("coding_agent", description="coding_agent|batch_extraction|interactive_chat|translation|research"),
                     limit: int = Query(10, le=25)):
    """Best value models for a specific workload type."""
    data = _load_snapshot_data()
    wl = workloads.get_workload(workload)
    if not wl:
        return {"error": f"Unknown workload: {workload}", "available": [w["name"] for w in workloads.list_workloads()]}

    scored = []
    for o in data["offers"]:
        if o.get("free"):
            score = 10000  # free wins for any workload
        else:
            in_cost = (o.get("input_per_m") or 0) * wl.get("tokens_per_job", 1000) / 1e6
            out_cost = (o.get("output_per_m") or 0) * wl.get("tokens_per_job", 1000) / 1e6
            total_cost = in_cost + out_cost
            if total_cost == 0:
                score = 0
            else:
                score = round(100 / total_cost, 1) if total_cost > 0 else 0
        scored.append({**o, "workhorse_score": score, "workload": workload})

    scored.sort(key=lambda x: x["workhorse_score"], reverse=True)
    return {"workload": workload, "workloads": [w["name"] for w in workloads.list_workloads()],
            "picks": scored[:limit], "count": len(scored), "timestamp": time.time()}


@app.get("/sources/health")
def sources_health():
    """Source health status."""
    health = source_health.get_health()
    sources = [{"source_id": s.source_id, "name": s.name, "enabled": s.enabled,
                "cadence_minutes": s.cadence_minutes, "consecutive_failures": s.consecutive_failures}
               for s in registry.get_all_sources()]
    return {"sources": sources, "health": health, "timestamp": time.time()}


@app.get("/events")
def list_events(limit: int = Query(50, le=200)):
    """Recent promotion events."""
    events = _load_events()
    return {"events": events[:limit], "count": len(events), "timestamp": time.time()}


@app.get("/api/stats")
def stats():
    """Overall stats."""
    data = _load_snapshot_data()
    events = _load_events()
    free_count = sum(1 for o in data["offers"] if o.get("free"))
    providers = set(o.get("provider_id", "") for o in data["offers"])
    return {
        "total_offers": data["count"],
        "free_offers": free_count,
        "providers": len(providers),
        "provider_list": sorted(providers),
        "total_events": len(events),
        "timestamp": time.time(),
    }


# --- Custom Categorizations (the CoinGecko layer) ---

@app.get("/categories")
def list_cats():
    """List all available deal categories."""
    return {"categories": categories.list_categories()}


@app.get("/categories/{category}")
def get_category(category: str, limit: int = Query(15, le=50)):
    """Get a specific deal category."""
    return categories.get_category(category, limit)


@app.get("/providers")
def list_providers():
    """Full provider comparison — setup difficulty, free tier, features, T&C."""
    return categories.provider_comparison()


@app.get("/providers/{provider_id}")
def get_provider(provider_id: str):
    """Detailed provider info — setup steps, T&C, rate limits, agentic notes."""
    p = providers_mod.get_provider(provider_id)
    if not p:
        return {"error": f"Unknown provider: {provider_id}", "available": list(providers_mod.PROVIDERS.keys())}
    return providers_mod.to_dict(p)


@app.get("/providers/{provider_id}/setup")
def provider_setup(provider_id: str):
    """Step-by-step setup instructions for a provider."""
    p = providers_mod.get_provider(provider_id)
    if not p:
        return {"error": f"Unknown provider: {provider_id}"}
    return {
        "provider": p.name,
        "difficulty": p.setup_difficulty,
        "difficulty_label": ["", "Instant", "Account required", "Approval needed", "Enterprise"][p.setup_difficulty],
        "steps": p.setup_steps,
        "signup_url": p.signup_url,
        "api_docs_url": p.api_docs_url,
        "free_tier": p.free_tier,
        "tos_highlights": p.tos_highlights,
    }


@app.get("/workload/{workload}")
def workload_picks(workload: str, limit: int = Query(10, le=25)):
    """Best models for a specific workload type with full reasoning."""
    data = _load_snapshot_data()
    wl = workloads.get_workload(workload)
    if not wl:
        return {"error": f"Unknown workload: {workload}", "available": [w["name"] for w in workloads.list_workloads()]}

    scored = []
    for o in data["offers"]:
        if o.get("free"):
            score = 10000
        else:
            in_cost = (o.get("input_per_m") or 0) * wl.get("tokens_per_job", 1000) / 1e6
            out_cost = (o.get("output_per_m") or 0) * wl.get("tokens_per_job", 1000) / 1e6
            total_cost = in_cost + out_cost
            score = round(100 / total_cost, 1) if total_cost > 0 else 0

        # Get provider metadata
        pid = o.get("provider_id", "")
        prov = providers_mod.get_provider(pid)
        prov_dict = providers_mod.to_dict(prov) if prov else {}

        scored.append({
            **o,
            "workhorse_score": score,
            "workload": workload,
            "setup_difficulty": prov_dict.get("setup_difficulty", 3),
            "setup_steps": prov_dict.get("setup_steps", []),
            "agentic_notes": prov_dict.get("agentic_notes", ""),
            "rate_limit_notes": prov_dict.get("rate_limit_notes", ""),
        })

    scored.sort(key=lambda x: x["workhorse_score"], reverse=True)
    return {
        "workload": workload,
        "workloads": [w["name"] for w in workloads.list_workloads()],
        "picks": scored[:limit],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("DEALRADAR_V2_PORT", "8800")))
# DEPRECATED: Use api_canonical.py (port 8803) instead
