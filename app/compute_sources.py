#!/usr/bin/env python3
"""app/compute_sources.py — the free-pool compute-source registry (non-API inference classes).

Models the "effectively unlimited" free-compute sources (from FREE-COMPUTE-SOURCES.md) as router tiers,
DISTINCT from the API providers in the canonical DB. The router's free pool = these classes + the API
free tiers. Each source knows: which class, reachable-from-this-box or documented-only, the order in
the free-pool ladder, and what it's good for.
"""
from __future__ import annotations

# class → {order, reachable, kind, models, cost, capacity, best_for, setup}
COMPUTE_SOURCES = {
    "webllm": {
        "class": "user-hardware", "order": 0, "reachable_from_box": False,
        "kind": "browser-inference", "cost_per_token": 0.0,
        "capacity": "unlimited (user GPU)", "models": ["qwen-small", "llama-3.2", "gemma"],
        "best_for": "classify/extract/rerank/summarize/RAG/JSON — the boring 80%",
        "setup": "client-side (WebGPU); the API serves the page, inference runs in the browser",
    },
    "chrome-nano": {
        "class": "user-hardware", "order": 1, "reachable_from_box": False,
        "kind": "browser-inference", "cost_per_token": 0.0,
        "capacity": "unlimited (local)", "models": ["gemini-nano"],
        "best_for": "simple client-side AI (Chrome built-in Prompt API)",
        "setup": "browser built-in; no deploy",
    },
    "petals": {
        "class": "volunteer-swarm", "order": 2, "reachable_from_box": True,
        "kind": "distributed-inference", "cost_per_token": 0.0,
        "capacity": "nearly unlimited (community)", "models": ["llama-3.1-405b", "mixtral-8x22b"],
        "best_for": "bulk experimental research where speed doesn't matter",
        "setup": "pip install petals; connect to public swarm (slow, ~4-6 tok/s, not private)",
    },
    "oracle-a1": {
        "class": "always-free-vm", "order": 3, "reachable_from_box": False,
        "kind": "self-hosted-local", "cost_per_token": 0.0,
        "capacity": "24/7 continuous", "models": ["qwen-small", "gemma", "llama-3.2 quantized"],
        "best_for": "a permanent private small-model daemon (llama.cpp OpenAI-compatible server)",
        "setup": "Oracle Always Free ARM VM (2 OCPU/12GB); needs an account",
    },
    "kaggle": {
        "class": "batch-gpu", "order": 4, "reachable_from_box": False,
        "kind": "batch-inference", "cost_per_token": 0.0,
        "capacity": "~30 GPU hr/wk + 20 TPU hr/wk", "models": ["any open model that fits"],
        "best_for": "processing large datasets in batch (50k docs)",
        "setup": "external platform; notebook/batch workloads only",
    },
    "colab": {
        "class": "opportunistic", "order": 5, "reachable_from_box": False,
        "kind": "batch-inference", "cost_per_token": 0.0,
        "capacity": "dynamic/unpublished", "models": ["GPUs/TPUs"],
        "best_for": "experimentation when available",
        "setup": "external; opportunistic, not infrastructure",
    },
    "hf-zerogpu": {
        "class": "collective", "order": 6, "reachable_from_box": False,
        "kind": "collective-compute", "cost_per_token": 0.0,
        "capacity": "daily quota/queues", "models": ["huge range"],
        "best_for": "occasional specialist/image/OCR/speech models",
        "setup": "HF Spaces ZeroGPU; don't hammer public Spaces",
    },
    "puter": {
        "class": "user-pays", "order": 7, "reachable_from_box": False,
        "kind": "user-supplied-allowance", "cost_per_token": 0.0,
        "capacity": "unlimited for an app (users pay)", "models": ["400+ models"],
        "best_for": "a public AI tool where users supply their own compute",
        "setup": "needs a Puter.js app + key; the developer bill stays $0",
    },
}

# the free-pool ladder ORDER (how the router tries sources)
FREE_POOL_ORDER = sorted(COMPUTE_SOURCES, key=lambda k: COMPUTE_SOURCES[k]["order"])


def reachable_from_box() -> list[str]:
    """The compute sources actually usable from THIS server box."""
    return [k for k in FREE_POOL_ORDER if COMPUTE_SOURCES[k]["reachable_from_box"]]


def free_pool() -> dict:
    """The full free-pool ladder (all classes, in order)."""
    return {"order": FREE_POOL_ORDER,
            "reachable_from_box": reachable_from_box(),
            "sources": COMPUTE_SOURCES}


def as_router_tiers() -> list[dict]:
    """The free-pool sources as router tiers (cost-free, before the paid API tiers)."""
    return [{"tier": i, "name": k, "class": COMPUTE_SOURCES[k]["class"],
             "reachable_from_box": COMPUTE_SOURCES[k]["reachable_from_box"],
             "cost_per_token": 0.0, "models": COMPUTE_SOURCES[k]["models"],
             "best_for": COMPUTE_SOURCES[k]["best_for"]}
            for i, k in enumerate(FREE_POOL_ORDER)]


if __name__ == "__main__":
    import json
    print(json.dumps({"free_pool_order": FREE_POOL_ORDER,
                      "reachable_from_box": reachable_from_box()}, indent=1))
