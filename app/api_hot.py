#!/usr/bin/env python3
"""app/api_hot.py — Hot Router API: OpenAI-compatible /v1/chat/completions.

The killer interface:

  POST /v1/chat/completions
  model: "hot/workhorse"
  model: "hot/free"
  model: "hot/coding"
  model: "hot/agentic"
  model: "hot/frontier"
  model: "hot/auto"

  with routing policies:
  {
    "routing": {
      "quality_floor": 0.85,
      "max_cost_usd": 0.10,
      "prefer_free": true,
      "max_latency_ms": 5000,
      "allow_escalation": true
    }
  }

This routes through the deal database + scoring engine + quota shadow pricing
to find the cheapest provider/model for the exact call.
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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import scoring
import router as hot_router
import providers as providers_mod

app = FastAPI(title="Hot Router", version="1.0",
              description="OpenAI-compatible chat completions with intelligent routing")
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


# Hot model aliases
HOT_ALIASES = {
    "hot/workhorse": {"role": "worker", "priority": "value"},
    "hot/free": {"role": "worker", "priority": "value", "free_only": True},
    "hot/coding": {"task": "coding", "role": "worker"},
    "hot/agentic": {"task": "agentic", "role": "worker"},
    "hot/frontier": {"role": "planner", "priority": "quality"},
    "hot/cheap": {"role": "worker", "priority": "cost"},
    "hot/fast": {"role": "worker", "priority": "speed"},
    "hot/auto": {},  # let the router decide everything
}


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "hot/auto"
    messages: list[ChatMessage] = []
    temperature: float = 0.7
    max_tokens: int | None = None
    routing: dict | None = None  # {"quality_floor": 0.85, "max_cost_usd": 0.10, ...}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """OpenAI-compatible chat completions with Hot Router intelligence."""
    offers = _load_offers()
    if not offers:
        return {"error": "No offers available — run discovery first"}

    # Parse the last user message
    query = ""
    for msg in reversed(req.messages):
        if msg.role == "user":
            query = msg.content
            break

    if not query:
        query = " ".join(m.content for m in req.messages)

    # Resolve hot alias
    model = req.model
    route_config = {}
    if model.startswith("hot/"):
        alias = HOT_ALIASES.get(model, {})
        route_config.update(alias)
        if req.routing:
            route_config.update(req.routing)
    elif req.routing:
        route_config.update(req.routing)

    # Apply routing policy
    lambda_val = 0.5
    quality_floor = route_config.get("quality_floor", 0.7)
    budget = route_config.get("max_cost_usd")

    if route_config.get("priority") == "quality":
        lambda_val = 0.2
    elif route_config.get("priority") == "cost":
        lambda_val = 0.8
    elif route_config.get("priority") == "speed":
        lambda_val = 0.6

    # Filter free if requested
    offers_to_route = offers
    if route_config.get("free_only"):
        offers_to_route = [o for o in offers if o.get("free")]

    # Create router
    r = hot_router.HotRouter(
        offers=offers_to_route,
        lambda_val=lambda_val,
        quality_floor=quality_floor,
        budget=budget,
    )

    # Route
    result = r.route(
        query=query,
        task=route_config.get("task"),
        role=route_config.get("role"),
    )

    if "error" in result:
        return result

    # Build OpenAI-compatible response
    return {
        "id": f"hotcmpl-{int(time.time()*1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result["model"],
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"[Hot Router: routed to {result['model']}@{result['provider']} "
                           f"(task={result['task']}, difficulty={result['difficulty']}, "
                           f"confidence={result['confidence']}, escalated={result['escalated']}, "
                           f"cost=${result['effective_cost']:.4f})]",
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "_hot_router": {
            "model": result["model"],
            "provider": result["provider"],
            "task": result["task"],
            "difficulty": result["difficulty"],
            "confidence": result["confidence"],
            "escalated": result["escalated"],
            "routing_score": result["routing_score"],
            "badges": result["badges"],
            "vector": result["vector"],
            "effective_cost_per_task": result["effective_cost"],
            "lambda": result["lambda"],
            "why": result["why"],
            "session_remaining": result.get("session_remaining"),
        },
    }


@app.get("/v1/models")
def list_hot_models():
    """List available hot/ model aliases."""
    return {
        "data": [
            {"id": alias, "object": "model", "owned_by": "hot-router"}
            for alias in HOT_ALIASES
        ]
    }


@app.get("/health")
def health():
    return {"status": "ok", "router": "hot", "version": "1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("HOT_PORT", "8802")))
# DEPRECATED: Use api_canonical.py (port 8803) instead
