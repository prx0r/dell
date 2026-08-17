#!/usr/bin/env python3
"""app/api.py — the deal-radar API (the standalone live-updating canonical resource).

Exposes the normalized LLM model DB + the value frontiers + deals + the router query endpoint.
Poll structured catalogs every 6h; this API serves the canonical snapshot (compute-on-write).

Endpoints:
  /health
  /models?search=&provider=&sort=value|price|quality&free=     list models
  /frontiers?mode=chat|all                                       the Pareto frontiers
  /deals                                                         free-tier + subsidy signals
  /route?task=coding&min_quality=&prefer_free=true               the router query (top pick)
  /refresh                                                       re-normalize from all sources
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

from fastapi import FastAPI, HTTPException, Query, Response
import normalize
import quality
import compute_sources
import task_ranking
import rate_limits
import canary
import benchmark_quality
import layer_recommend
import advanced_query

app = FastAPI(title="Pāṭala Deal Radar", version="0.1",
              description="Live LLM pricing + quality + value frontiers (canonical, compute-on-write)")


def _db():
    if not (ROOT / "data" / "canonical-models.json").exists():
        normalize.normalize()
    return json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8"))


@app.get("/health")
def health():
    d = _db()
    return {"models": d.get("count"), "fetched_at": d.get("fetched_at"),
            "provenance": {"api_version": "1.0", "surface": "deal-radar", "served": "canonical-db"}}


def _env(**extra):
    return {"api_version": "1.0", "surface": "deal-radar", "served": "canonical-db", **extra}


def _cache(response: Response, body: dict, max_age: int = 3600):
    """Set ETag + immutable-ish cache headers on a response for agent caching (perf rule 8/9)."""
    import hashlib
    etag = '"' + hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16] + '"'
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = f"public, max-age={max_age}, stale-while-revalidate=86400"
    return etag


@app.get("/models")
def list_models(search: str | None = None, provider: str | None = None,
                sort: str = "value", free: bool | None = None, modality: str | None = None,
                limit: int = Query(20, le=100)):
    d = _db()
    models = d.get("models", {})
    aa = quality.fetch_aa_quality()
    out = []
    for mid, rec in models.items():
        # default: real text-LLM chat models (consistent with /frontiers chat mode)
        low = mid.lower()
        prov_low = (rec.get("provider") or "").lower()
        if any(x in low for x in ("embedding", "embed", "audio", "tts", "stt", "image",
                                  "stable-diffusion", "flux", "dall-e", "sdxl", "whisper",
                                  "/e5-", "bge-", "rerank", "colbert", "ollama/", "sample_spec",
                                  "1024", "canvas", "playground", "bedrock/")):
            continue
        if "embedding" in prov_low:
            continue  # provider-level embedding model (e.g. fireworks_ai-embedding-models)
        if search and search.lower() not in mid.lower():
            continue
        if provider and rec.get("provider") != provider:
            continue
        if free is not None and bool(rec.get("free")) != free:
            continue
        if modality and modality not in (rec.get("input_modalities") or []):
            continue  # modality filter (vision/audio/video/pdf/text) — the agent's "cheap vision model" query
        q = aa.get(mid) or quality.quality_for(mid, rec.get("provider", ""))
        if isinstance(q, dict) and "scores" not in q:
            q = {"scores": q, "source": "measured"}
        vs = quality.value_score(rec, q.get("scores", {}))
        out.append({"model": mid, "provider": rec.get("provider"),
                    "prompt_per_token": rec.get("prompt_per_token"),
                    "completion_per_token": rec.get("completion_per_token"),
                    "context": rec.get("context"), **vs,
                    "input_modalities": rec.get("input_modalities", []),
                    "reasoning": rec.get("reasoning", False),
                    "tool_call": rec.get("tool_call", False),
                    "quality_source": q.get("source", "estimated"),
                    "source": rec.get("source")})
    key = {"value": lambda s: s["value"], "price": lambda s: -s["cost_per_job"],
           "quality": lambda s: -s["quality"]}.get(sort, lambda s: s["value"])
    if sort == "price":
        # a $0 'price' is local/broken data, not a real deal — exclude it from price ranking
        out = [m for m in out if m.get("cost_per_job", 0) > 0]
    out.sort(key=key, reverse=True)
    return {"count": len(out), "models": out[:limit], "fetched_at": d.get("fetched_at"),
            "provenance": _env()}


@app.get("/frontiers")
def get_frontiers(mode: str = "chat", limit: int = Query(8, le=20)):
    f = quality.frontiers(mode=mode, limit=limit)
    f["provenance"] = _env()
    return f


@app.get("/deals")
def get_deals():
    d = quality.deals()
    d["provenance"] = _env()
    return d


@app.get("/compute-sources")
def get_compute_sources():
    """The non-API free-pool compute sources (WebLLM/Petals/Oracle/Kaggle/etc.) as router tiers."""
    fp = compute_sources.free_pool()
    fp["provenance"] = _env()
    return fp


@app.get("/free-pool")
def get_free_pool():
    """The free-pool sources as router tiers, ordered (free-first)."""
    tiers = compute_sources.as_router_tiers()
    return {"tiers": tiers, "reachable_from_box": compute_sources.reachable_from_box(),
            "provenance": _env()}


@app.get("/recommend")
def recommend(task: str = Query("coding", description="coding|research|extraction|long-context|reasoning"),
              min_quality: float = 0.0, prefer_free: bool = False,
              format: str = Query("full", description="full|compact — compact is token-minimal for agents"),
              limit: int = Query(10, le=25),
              response: Response = None):
    """The task-aware agent-performance recommendation: best model for THIS task type,
    ranked by quality × success / effective_cost, with per-axis breakdown."""
    if task not in task_ranking.TASKS:
        raise HTTPException(400, {"error": {"code": "BAD_TASK", "message": f"unknown task {task}; "
                                             f"use {task_ranking.TASKS}", "retryable": False}})
    db = _db()
    models = db.get("models", {})
    ranking = task_ranking.rank(models, quality.fetch_aa_quality(), task=task,
                                min_quality=min_quality, prefer_free=prefer_free, limit=limit)
    if format == "compact":
        # token-minimal: just model + provider + the decision-relevant score
        compact = [{"model": r["model"], "provider": r["provider"],
                    "score": r["score"], "q": r["task_quality"],
                    "cost": r["cost_per_task"], "free": r["free"]}
                   for r in ranking]
        body = {"task": task, "picks": compact, "provenance": _env()}
        if response is not None:
            _cache(response, body)
        return body
    body = {"task": task, "min_quality": min_quality, "prefer_free": prefer_free,
            "ranking": ranking, "tasks": task_ranking.TASKS, "provenance": _env()}
    if response is not None:
        _cache(response, body)
    return body


@app.get("/tasks")
def get_tasks():
    """The task profiles (per-axis weights + success + latency sensitivity)."""
    return {"tasks": task_ranking.TASKS, "profiles": task_ranking.TASK_PROFILES,
            "provenance": _env()}


@app.get("/benchmarks")
def get_benchmarks(task: str = Query("coding", description="coding|reasoning|research|extraction"),
                   limit: int = Query(10, le=25)):
    """The REAL measured benchmark leaders for a task (SWE-Bench / GPQA / etc.) — quality_source=measured."""
    if task not in benchmark_quality.TASK_BENCHMARKS:
        raise HTTPException(400, {"error": {"code": "BAD_TASK", "message": f"unknown task {task}",
                                            "retryable": False}})
    return {"task": task, "benchmarks": benchmark_quality.top_benchmarked(task, limit),
            "provenance": _env()}


@app.get("/recommend-layer")
def recommend_layer(layer: str = Query("T1", description="T1|ARGMAP|L2|L200|C1|L0|L1"),
                    limit: int = Query(3, le=5)):
    """The best model for a TRANSLATION layer (per the per-layer translation stack): maps each layer to
    a task and ranks by measured benchmark quality. For setting HERMES_MODEL per layer worker."""
    if layer.upper() not in layer_recommend.LAYER_MAP:
        raise HTTPException(400, {"error": {"code": "BAD_LAYER", "message": f"unknown layer {layer}",
                                            "retryable": False}})
    r = layer_recommend.recommend_layer(layer, limit=limit)
    r["provenance"] = _env()
    return r


@app.get("/layer-config")
def get_layer_config():
    """The full per-layer model config (worker-consumable: layer → model + task + why) for HERMES_MODEL."""
    cfg = layer_recommend.layer_config()
    cfg["provenance"] = _env()
    return cfg


@app.get("/ask")
def ask(query: str = Query(..., description="natural-language model query, e.g. 'image model for batch work' or 'image model for 4 calls per day'"),
        limit: int = Query(5, le=10)):
    """The advanced natural-language model recommendation. Parses the query → usage profile
    (task/modality/batch/daily-calls) → volume-tuned utility recommendation + rate-limit annotation."""
    r = advanced_query.recommend_for_query(query, limit=limit)
    r["provenance"] = _env()
    return r


@app.get("/rate-limits")
def get_rate_limits():
    """Per-provider rate + token limits (esp. the free tiers) — how much each gives you."""
    rl = rate_limits.all_rate_limits()
    rl["provenance"] = _env()
    return rl


@app.get("/canary")
def get_canary():
    """The last provider live-check (canary-report.json): is each free endpoint actually alive?"""
    p = ROOT / "data" / "canary-report.json"
    if not p.exists():
        return {"status": "never_run", "note": "run app/canary.py (cron daily) to probe providers",
                "provenance": _env()}
    d = json.loads(p.read_text(encoding="utf-8"))
    d["provenance"] = _env()
    return d


@app.get("/validation")
def get_validation():
    """The last price-validation report (cron): were cached prices verified against live sources?"""
    p = ROOT / "data" / "validation-report.json"
    if not p.exists():
        return {"status": "never_run", "note": "run app/refresh.py (cron) to validate prices",
                "provenance": _env()}
    d = json.loads(p.read_text(encoding="utf-8"))
    d["provenance"] = _env()
    return d


@app.get("/route")
def route(task: str = "coding", min_quality: float = 40.0, prefer_free: bool = True,
          limit: int = Query(5, le=10)):
    """The router query: top pick for a task, free-first, quality-floored."""
    f = quality.frontiers(mode="chat", limit=50)
    cands = f.get("best_value_paid", []) + f.get("top_free", [])
    scored = []
    for c in cands:
        q = c.get("quality", 0)
        if q < min_quality:
            continue
        is_free = c.get("free", False)
        if prefer_free and not is_free:
            # paid candidates still allowed but scored lower
            score = c.get("value") * 0.5
        else:
            score = c.get("value")
        scored.append({"model": c.get("model"), "provider": c.get("provider"),
                       "quality": q, "cost_per_job": c.get("cost_per_job"),
                       "free": is_free, "score": round(score, 1)})
    scored.sort(key=lambda s: -s["score"])
    return {"task": task, "min_quality": min_quality, "prefer_free": prefer_free,
            "picks": scored[:limit], "provenance": _env()}


@app.post("/refresh")
def refresh():
    n = normalize.normalize()
    return {"models": len(n), "note": "re-pulled all sources"}


@app.get("/capabilities")
def capabilities():
    """Provider health + hotswap status. Shows which data sources are healthy, which failed.
    "Tools don't become truth. Their outputs become observations." — newbuild"""
    from capability_registry import get_registry
    reg = get_registry()
    return {
        "capabilities": reg.capability_summary(),
        "health": reg.health_status(),
        "provenance": _env(),
    }


@app.get("/patala/layer-config")
def patala_layer_config(layer: str | None = None):
    """OpenPāṭala Factory integration: best model per translation layer (T1/L0/ARGMAP/L2/L200/C1).
    Set HERMES_MODEL per layer in the translation stack."""
    import layer_recommend
    if layer:
        return {"layer": layer, **layer_recommend.recommend_layer(layer, limit=3),
                "provenance": _env()}
    return {"config": layer_recommend.layer_config(), "provenance": _env()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("DEALRADAR_PORT", "8799")))
