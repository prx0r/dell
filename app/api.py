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

from fastapi import FastAPI, HTTPException, Query
import normalize
import quality

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


@app.get("/models")
def list_models(search: str | None = None, provider: str | None = None,
                sort: str = "value", free: bool | None = None, limit: int = Query(20, le=100)):
    d = _db()
    models = d.get("models", {})
    aa = quality.fetch_aa_quality()
    out = []
    for mid, rec in models.items():
        # default: real text-LLM chat models (consistent with /frontiers chat mode)
        low = mid.lower()
        if any(x in low for x in ("embedding", "embed", "audio", "tts", "stt", "image",
                                  "stable-diffusion", "flux", "dall-e", "sdxl", "whisper",
                                  "/e5-", "bge-", "rerank", "colbert", "ollama/", "sample_spec",
                                  "1024", "canvas", "playground", "bedrock/")):
            continue
        if search and search.lower() not in mid.lower():
            continue
        if provider and rec.get("provider") != provider:
            continue
        if free is not None and bool(rec.get("free")) != free:
            continue
        q = aa.get(mid, quality.quality_for(mid, rec.get("provider", "")))
        vs = quality.value_score(rec, q)
        out.append({"model": mid, "provider": rec.get("provider"),
                    "prompt_per_token": rec.get("prompt_per_token"),
                    "completion_per_token": rec.get("completion_per_token"),
                    "context": rec.get("context"), **vs, "source": rec.get("source")})
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("DEALRADAR_PORT", "8799")))
