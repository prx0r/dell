#!/usr/bin/env python3
"""mcp/server.py — the garglecum MCP server (goal-oriented tools, MCP SDK v2 high-level MCPServer).

Per the perf doctrine: "fewer, goal-oriented tools work better for agents." Instead of exposing 14 raw
HTTP endpoints, this MCP server exposes goal-oriented tools:

  pick_model(task, min_quality, prefer_free)   → best model for THIS task
  check_live_prices()                          → price-health (canary + validation)
  get_model_details(model, task)               → granular detail + measured benchmark quality
  get_free_sources()                           → free-pool + rate limits
  recommend_model_for_layer(layer)             → OpenPāṭala Factory: best model per translation layer
  get_capability_health()                      → NEW: provider health + hotswap status

"Tools don't become truth. Their outputs become observations." — newbuild

Tools call the API modules directly (no HTTP round-trip). Compact (token-minimal).
The input schema is derived from the typed function signatures (MCP SDK v2 tool decorator).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

from mcp.server.mcpserver import MCPServer

import task_ranking
import quality
import benchmark_quality
import compute_sources
import rate_limits
import canary
import layer_recommend
import advanced_query

server = MCPServer(name="garglecum")


def _db():
    import normalize
    if not (ROOT / "data" / "canonical-models.json").exists():
        normalize.normalize()
    return json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8"))


@server.tool()
def pick_model(task: str = "coding", min_quality: float = 40.0,
               prefer_free: bool = False, limit: int = 5) -> dict:
    """Best models for a task type (coding/research/extraction/long-context/reasoning),
    ranked by measured quality × success / effective cost. Compact decision-relevant fields."""
    ranking = task_ranking.rank(_db().get("models", {}), quality.fetch_aa_quality(),
                                task=task, min_quality=min_quality, prefer_free=prefer_free, limit=limit)
    return {"task": task, "picks": [{"model": r["model"], "provider": r["provider"],
                                     "score": r["score"], "q": r["task_quality"],
                                     "cost": r["cost_per_task"], "free": r["free"]} for r in ranking]}


@server.tool()
def check_live_prices() -> dict:
    """The current price-health: last refresh time + canary (which free providers are live now)
    + validation (cached vs live drift). Tells an agent if prices are trustworthy."""
    p = ROOT / "data" / "validation-report.json"
    v = json.loads(p.read_text()).get("summary", {}) if p.exists() else {"status": "never_run"}
    return {"fetched_at": _db().get("fetched_at"), "validation": v, "canary": canary.run().get("summary")}


@server.tool()
def get_model_details(model: str, task: str = "coding") -> dict:
    """Full granular detail for one model: price, context, modalities, capabilities, and the
    MEASURED benchmark quality for the task. quality_source tells measured vs estimated."""
    db = _db().get("models", {})
    rec = db.get(model)
    if not rec:
        base = model.split("/")[-1].lower()
        for mid, r in db.items():
            if base in mid.lower() and len(base) >= 4:
                rec, model = r, mid
                break
    if not rec:
        return {"error": f"model {model} not found", "quality_source": "not_found"}
    bq = benchmark_quality.benchmark_quality(model, task)
    return {"model": model, "provider": rec.get("provider"),
            "prompt_per_token": rec.get("prompt_per_token"),
            "completion_per_token": rec.get("completion_per_token"),
            "context": rec.get("context"),
            "input_modalities": rec.get("input_modalities", []),
            "reasoning": rec.get("reasoning"), "tool_call": rec.get("tool_call"),
            "open_weights": rec.get("open_weights"),
            "task_quality": {"score": bq["score"], "source": bq["source"], "benchmark": bq["benchmark"]},
            "free": rec.get("free")}


@server.tool()
def get_free_sources() -> dict:
    """The free-compute pool: the non-API free sources (WebLLM/Petals/Oracle/etc. as router tiers)
    + the per-provider rate limits (rpm/rpd/tokens for free tiers)."""
    return {"free_pool": compute_sources.free_pool(), "rate_limits": rate_limits.all_rate_limits()}


@server.tool()
def recommend_model_for_layer(layer: str = "T1", limit: int = 3) -> dict:
    """The best model for a TRANSLATION layer (T1/ARGMAP/L2/L200/C1), ranked by measured benchmark
    quality for the layer's task. Use to set HERMES_MODEL per layer in the translation stack."""
    return layer_recommend.recommend_layer(layer, limit=limit)


@server.tool()
def recommend_for_query(query: str, limit: int = 5) -> dict:
    """Recommend a model from a natural-language query (e.g. 'image model for batch work' vs
    'image model for 4 calls per day'). The algorithm computes the usage profile + volume strategy +
    per-model utility/value/reason, so the LLM gets the granular reasoning AND can dig into the data.
    Ordering: free-first, then value (quality/cost)."""
    return advanced_query.analyze(query, limit=limit)


@server.tool()
def get_capability_health() -> dict:
    """Provider health + hotswap status. Shows which data sources are healthy, which failed,
    and which models were skipped due to provider failure. "Tools don't become truth." """
    from capability_registry import get_registry
    reg = get_registry()
    return {
        "capabilities": reg.capability_summary(),
        "health": reg.health_status(),
    }


def main():
    import anyio
    anyio.run(server.run_stdio_async)


if __name__ == "__main__":
    main()
