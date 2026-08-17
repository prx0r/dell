#!/usr/bin/env python3
"""app/api_v3.py — The Job-First Agentic API.

"The fundamental unit should not be: model → intelligence score → price.
It should be: I have this job. What is the cheapest model/provider/deal I can trust to do it?"

Five homepage questions:
  🔥 HOTTEST DEAL       Best exceptional opportunity right now
  🐎 BEST WORKHORSE     Most intelligence per practical dollar
  🧠 BIG BRAIN          Best model when quality matters
  🐜 BEST CHEAP WORKER  Best for agents / bulk inference
  🆓 BEST FREE          Best useful $0 option
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
from pydantic import BaseModel

import scoring
import providers as providers_mod

app = FastAPI(title="LLM Deals", version="3.0",
              description="Job-first LLM inference deal intelligence — 'I have this job, what should I use?'")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _load_offers() -> list[dict]:
    snapshots_dir = ROOT / "snapshots"
    offers = []
    if snapshots_dir.exists():
        for f in snapshots_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                offers.extend(data.get("offers", []))
            except Exception:
                continue
    return offers


# --- The 5 Homepage Questions ---

@app.get("/")
def homepage():
    """The 5 questions the homepage answers."""
    return {
        "name": "LLM Deals",
        "tagline": "I have this job. What is the cheapest model I can trust to do it?",
        "questions": [
            {"url": "/best/hot-deal", "label": "🔥 HOTTEST DEAL", "description": "Best exceptional opportunity right now"},
            {"url": "/best/workhorse", "label": "🐎 BEST WORKHORSE", "description": "Most intelligence per practical dollar"},
            {"url": "/best/big-brain", "label": "🧠 BIG BRAIN", "description": "Best model when quality matters"},
            {"url": "/best/worker", "label": "🐜 BEST CHEAP WORKER", "description": "Best for agents / bulk inference"},
            {"url": "/best/free", "label": "🆓 BEST FREE", "description": "Best useful $0 option"},
        ],
        "verticals": ["/best/coding", "/best/agentic", "/best/research", "/best/writing",
                       "/best/rag", "/best/vision", "/best/long-context"],
        "api": "POST /v1/recommend for structured recommendations",
    }


# --- /best/{badge} endpoints (also at /v1/best/{badge} per apiuse.md spec) ---

@app.get("/best/{badge}")
@app.get("/v1/best/{badge}")
def best_by_badge(badge: str, limit: int = Query(10, le=50)):
    """Get best models for a specific badge/category.
    Available: workhorse, big-brain, frontier, coder, agentic, worker, tool-caller,
    researcher, long-context, rag, writer, creative, vision, hidden-gem,
    punches-above, free, hot-deal, fast, daily-driver, planner, reviewer"""
    offers = _load_offers()
    if not offers:
        return {"badge": badge, "picks": [], "count": 0, "note": "No data — run discovery first"}

    scored = [scoring.score_and_badge(o, providers_mod.PROVIDERS.get(o.get("provider_id", ""))) for o in offers]
    badged = [s for s in scored if badge in s["badges"]]
    badged.sort(key=lambda x: x["vector"]["workhorse"], reverse=True)

    return {
        "badge": badge,
        "badge_label": scoring.BADGE_LABELS.get(badge, badge),
        "picks": badged[:limit],
        "count": len(badged),
        "total_offers": len(offers),
    }


# --- POST /v1/recommend ---

class RecommendRequest(BaseModel):
    task: str = "coding_task"
    role: str = "worker"
    priority: str = "value"
    expected_input_tokens: int | None = None
    expected_output_tokens: int | None = None
    tool_calling: bool = False
    min_context: int = 0
    budget: float | None = None
    limit: int = 5


@app.post("/v1/recommend")
def recommend(req: RecommendRequest):
    """Task-first recommendation: 'I have this job, what should I use?' """
    offers = _load_offers()
    result = scoring.recommend(
        offers, task=req.task, role=req.role, priority=req.priority,
        min_context=req.min_context, tool_calling=req.tool_calling,
        budget=req.budget, limit=req.limit)
    return result


# --- GET /v1/recommend (query string version) ---

@app.get("/v1/recommend")
def recommend_get(
    task: str = Query("coding_task"),
    role: str = Query("worker"),
    priority: str = Query("value"),
    tool_calling: bool = Query(False),
    min_context: int = Query(0),
    budget: float | None = Query(None),
    limit: int = Query(5, le=20)):
    """GET version of recommend for quick queries."""
    offers = _load_offers()
    return scoring.recommend(
        offers, task=task, role=role, priority=priority,
        min_context=min_context, tool_calling=tool_calling,
        budget=budget, limit=limit)


# --- Task profiles ---

@app.get("/v1/tasks")
def list_tasks():
    """Available task profiles and their token expectations."""
    return {"tasks": scoring.TASK_PROFILES}


# --- Scoring vector for a model ---

@app.get("/v1/score/{model_id:path}")
def score_model(model_id: str):
    """Get the full 10-dimensional scoring vector for a model."""
    offers = _load_offers()
    matches = [o for o in offers if o.get("model_id") == model_id]
    if not matches:
        return {"error": f"Model not found: {model_id}"}

    results = []
    for o in matches:
        scored = scoring.score_and_badge(o, providers_mod.PROVIDERS.get(o.get("provider_id", "")))
        results.append({
            "model_id": scored.get("model_id"),
            "provider": scored.get("provider_id"),
            "vector": scored["vector"],
            "badges": scored["badges"],
            "effective_costs": scored["effective_costs"],
        })
    return {"model_id": model_id, "offerings": results}


# --- All badges ---

@app.get("/v1/badges")
def list_badges():
    """List all available badges with their scoring rules."""
    return {"badges": [{"id": b, "label": scoring.BADGE_LABELS.get(b, b)} for b in scoring.BADGE_RULES]}


# --- Stacks ---

@app.get("/v1/stacks")
def recommend_stack(
    task: str = Query("agentic_coding"),
    budget: float = Query(1.0),
    limit: int = Query(3)):
    """Recommend a full agent stack: planner + workers + reviewer."""
    offers = _load_offers()

    # Pick planner (frontier/big_brain)
    planner = scoring.recommend(offers, task=task, role="planner", budget=budget*0.4, limit=1)

    # Pick workers (cheap/fast)
    workers = scoring.recommend(offers, task=task, role="worker", budget=budget*0.4, limit=2)

    # Pick reviewer (smart/reliable)
    reviewer = scoring.recommend(offers, task=task, role="reviewer", budget=budget*0.2, limit=1)

    planner_cost = (planner.get("effective_cost_per_task") or 0) * 0.4
    worker_cost = sum((w.get("effective_cost_per_task") or 0) for w in workers.get("all_picks", [])) * 0.4
    reviewer_cost = (reviewer.get("effective_cost_per_task") or 0) * 0.2

    return {
        "task": task,
        "budget": budget,
        "stack": {
            "planner": planner.get("pick"),
            "workers": [w.get("model") for w in workers.get("all_picks", [])],
            "reviewer": reviewer.get("pick"),
        },
        "estimated_cost_per_task": round(planner_cost + worker_cost + reviewer_cost, 6),
        "details": {
            "planner": planner,
            "workers": workers,
            "reviewer": reviewer,
        },
    }


# --- Effective cost comparison ---

@app.get("/v1/costs")
def compare_costs(
    task: str = Query("coding_task"),
    limit: int = Query(20, le=50)):
    """Compare effective cost per task across models — the Databricks insight."""
    offers = _load_offers()
    scored = [scoring.score_and_badge(o) for o in offers]

    for s in scored:
        cost_data = s["effective_costs"].get(task, {})
        s["effective_cost"] = cost_data.get("effective_cost_per_task", 999)
        s["raw_cost"] = cost_data.get("raw_cost_per_task", 999)

    # Sort by effective cost (cheapest successful task first)
    scored.sort(key=lambda x: x["effective_cost"])
    return {
        "task": task,
        "task_description": scoring.TASK_PROFILES.get(task, {}).get("description", ""),
        "picks": scored[:limit],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("LLMDEALS_PORT", "8801")))
# DEPRECATED: Use api_canonical.py (port 8803) instead
