"""app/scoring.py — The multi-dimensional scoring vector engine.

Replaces single-score ranking with a 10-dimensional vector per model×provider×deal.
Badges are DERIVED from the vector, not assigned manually.

Core insight from apiuse.md:
- Models are Pareto fronts, not rankings
- A $0.10 model scoring 84 can be more interesting than a $20 model scoring 96
- Track $/successful task, not $/million tokens
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# --- The 10 scoring dimensions ---

DIMENSIONS = [
    "intelligence",   # raw capability (benchmarks, AA index)
    "workhorse",      # everyday dependability (success × reliability × speed ÷ cost)
    "value",          # intelligence per dollar
    "coding",         # software engineering capability
    "agentic",        # multi-step autonomous reliability
    "tool_calling",   # function/tool use accuracy
    "research",       # search + synthesis + sources
    "long_context",   # large document/repo handling
    "speed",          # tokens/sec, latency
    "reliability",    # uptime, consistency, low failure rate
]


def score_vector(offer: dict, provider_meta: dict = None) -> dict:
    """Compute the 10-dimensional score vector for a model×provider×deal.

    Returns dict with each dimension 0-100.
    """
    meta = offer.get("metadata", {})
    # Convert ProviderMeta to dict if needed
    if provider_meta and hasattr(provider_meta, '__dict__'):
        prov = {k: v for k, v in provider_meta.__dict__.items() if not k.startswith('_')}
    elif isinstance(provider_meta, dict):
        prov = provider_meta
    else:
        prov = {}

    # --- Intelligence (from AA index or capability estimates) ---
    aa_intel = meta.get("intelligence_index")
    if aa_intel is not None:
        # AA index ranges roughly 0-100, normalize
        intelligence = min(100, max(0, aa_intel))
    else:
        # Estimate from capabilities
        intelligence = 50
        if meta.get("coding_index"): intelligence = max(intelligence, meta["coding_index"])
        if meta.get("agentic_index"): intelligence = max(intelligence, meta["agentic_index"])
        if prov.get("has_reasoning"): intelligence += 10
        if prov.get("has_tool_calling"): intelligence += 5
        intelligence = min(100, intelligence)

    # --- Speed (from throughput/latency) ---
    tps = meta.get("throughput_tps")
    ttft = meta.get("ttft_seconds")
    latency_ms = prov.get("avg_latency_ms")
    if tps:
        speed = min(100, tps / 5)  # 500 tps = 100
    elif latency_ms:
        speed = max(0, 100 - latency_ms / 10)  # 0ms=100, 1000ms=0
    else:
        speed = 50  # unknown

    # --- Reliability (provider health + track record) ---
    reliability = 70  # baseline
    if prov.get("setup_difficulty", 3) <= 1: reliability += 10  # easy setup = reliable infra
    if prov.get("has_batch_api"): reliability += 5
    if meta.get("source_url", "").startswith("https://"): reliability += 5

    # --- Coding (from AA coding index or capability) ---
    coding = meta.get("coding_index") or intelligence * 0.9
    if prov.get("has_tool_calling"): coding = max(coding, coding * 1.05)

    # --- Agentic (from AA agentic index or tool calling + structured output) ---
    agentic = meta.get("agentic_index") or 40
    if prov.get("has_tool_calling"): agentic = max(agentic, agentic * 1.2 + 10)
    if prov.get("has_structured_output"): agentic += 10
    agentic = min(100, agentic)

    # --- Tool Calling ---
    tool_calling = 30  # baseline (not known)
    if prov.get("has_tool_calling"): tool_calling = 70
    if meta.get("supports_tools"): tool_calling = 85
    # Could be enriched with real tool-call reliability data from OpenRouter

    # --- Research ---
    research = intelligence * 0.85  # correlated with intelligence
    ctx = offer.get("context_tokens") or prov.get("context_window_max") or 0
    if ctx > 100000: research += 10

    # --- Long Context ---
    if ctx >= 1000000: long_context = 95
    elif ctx >= 200000: long_context = 85
    elif ctx >= 128000: long_context = 75
    elif ctx >= 32000: long_context = 50
    else: long_context = 20

    # --- Workhorse (the composite: success × reliability × speed ÷ cost) ---
    in_m = offer.get("input_per_m") or 0
    out_m = offer.get("output_per_m") or 0
    is_free = offer.get("free", False)

    # Effective cost (lower = better workhorse)
    if is_free:
        cost_score = 100
    elif in_m > 0:
        # $0.1/M = 90, $1/M = 60, $10/M = 20, $100/M = 5
        cost_score = max(0, min(100, 100 - (in_m * 8)))
    else:
        cost_score = 50

    workhorse = (
        min(100, coding) * 0.25 +      # task success
        reliability * 0.15 +             # dependability
        speed * 0.15 +                   # speed
        cost_score * 0.30 +             # effective cost
        (100 if prov.get("has_tool_calling") else 50) * 0.10 +  # agent stability
        min(100, long_context) * 0.05   # context utility
    )

    # --- Value (intelligence per dollar) ---
    if is_free:
        value = 100
    elif in_m > 0:
        value = min(100, (intelligence / max(in_m, 0.01)) * 2)
    else:
        value = 50

    return {
        "intelligence": round(intelligence, 1),
        "workhorse": round(workhorse, 1),
        "value": round(value, 1),
        "coding": round(min(100, coding), 1),
        "agentic": round(min(100, agentic), 1),
        "tool_calling": round(min(100, tool_calling), 1),
        "research": round(min(100, research), 1),
        "long_context": round(long_context, 1),
        "speed": round(speed, 1),
        "reliability": round(reliability, 1),
    }


# --- Badge derivation rules ---

BADGE_RULES = {
    "big_brain": lambda v: v["intelligence"] >= 85,
    "frontier": lambda v: v["intelligence"] >= 80 and v["coding"] >= 75,
    "workhorse": lambda v: v["workhorse"] >= 75,
    "daily_driver": lambda v: v["workhorse"] >= 70 and v["reliability"] >= 70 and v["speed"] >= 60,
    "fast": lambda v: v["speed"] >= 80,
    "worker": lambda v: v["workhorse"] >= 60 and v["value"] >= 70,
    "agentic": lambda v: v["agentic"] >= 70 and v["tool_calling"] >= 60,
    "tool_caller": lambda v: v["tool_calling"] >= 75,
    "coder": lambda v: v["coding"] >= 75,
    "planner": lambda v: v["intelligence"] >= 75 and v["research"] >= 70,
    "reviewer": lambda v: v["intelligence"] >= 80 and v["coding"] >= 70,
    "researcher": lambda v: v["research"] >= 75,
    "long_context": lambda v: v["long_context"] >= 80,
    "rag": lambda v: v["long_context"] >= 60 and v["speed"] >= 50,
    "writer": lambda v: v["intelligence"] >= 65,  # placeholder
    "creative": lambda v: v["intelligence"] >= 60,  # placeholder
    "vision": lambda v: False,  # needs modality data
    "hidden_gem": lambda v: v["value"] >= 80 and v["intelligence"] >= 50 and v["intelligence"] < 80,
    "punches_above": lambda v: v["value"] >= 85 and v["intelligence"] >= 40,
    "free": lambda v: False,  # set externally based on offer.free
    "hot_deal": lambda v: v["value"] >= 90,
}

BADGE_LABELS = {
    "big_brain": "🧠 Big Brain",
    "frontier": "🏆 Frontier",
    "workhorse": "🐎 Workhorse",
    "daily_driver": "🚗 Daily Driver",
    "fast": "⚡ Fast",
    "worker": "🐜 Worker",
    "agentic": "🤖 Agentic",
    "tool_caller": "🛠️ Tool Caller",
    "coder": "💻 Coder",
    "planner": "🧭 Planner",
    "reviewer": "🔍 Reviewer",
    "researcher": "📚 Researcher",
    "long_context": "📄 Long Context",
    "rag": "🧲 RAG",
    "writer": "✍️ Writer",
    "creative": "🎭 Creative",
    "vision": "👁️ Vision",
    "hidden_gem": "💎 Hidden Gem",
    "punches_above": "🥊 Punches Above Weight",
    "free": "🆓 Free",
    "hot_deal": "🔥 Hot Deal",
}


def derive_badges(vector: dict, offer: dict) -> list[str]:
    """Derive badge list from scoring vector + offer metadata."""
    badges = []
    for badge, rule in BADGE_RULES.items():
        try:
            if rule(vector):
                badges.append(badge)
        except Exception:
            pass

    # Free badge is special
    if offer.get("free"):
        badges.append("free")

    return badges


# --- Effective cost per task ---

# Task profiles: what a typical job looks like
TASK_PROFILES = {
    "coding_task": {
        "input_tokens": 8000,
        "output_tokens": 3000,
        "success_rate": 0.85,  # 85% of attempts succeed
        "description": "Typical coding task (edit, debug, implement)",
    },
    "agentic_coding": {
        "input_tokens": 40000,
        "output_tokens": 8000,
        "success_rate": 0.70,
        "description": "Multi-step agentic coding (plan → implement → verify)",
    },
    "extraction": {
        "input_tokens": 2000,
        "output_tokens": 500,
        "success_rate": 0.95,
        "description": "Data extraction from text",
    },
    "chat_turn": {
        "input_tokens": 1000,
        "output_tokens": 300,
        "success_rate": 0.98,
        "description": "Single chat turn",
    },
    "research_task": {
        "input_tokens": 15000,
        "output_tokens": 5000,
        "success_rate": 0.80,
        "description": "Research synthesis with sources",
    },
    "translation": {
        "input_tokens": 3000,
        "output_tokens": 3000,
        "success_rate": 0.90,
        "description": "Translation task",
    },
    "summarization": {
        "input_tokens": 10000,
        "output_tokens": 1000,
        "success_rate": 0.95,
        "description": "Summarize long document",
    },
}


def effective_cost_per_task(offer: dict, task: str = "coding_task") -> dict:
    """Calculate $/successful task, not $/million tokens.

    This is the key metric from Databricks' finding:
    cheaper tokens ≠ cheaper tasks if the model burns more tokens.
    """
    profile = TASK_PROFILES.get(task, TASK_PROFILES["coding_task"])
    in_m = offer.get("input_per_m") or 0
    out_m = offer.get("output_per_m") or 0
    is_free = offer.get("free", False)

    # Raw cost per task
    if is_free:
        raw_cost = 0.0
    else:
        input_cost = (in_m * profile["input_tokens"]) / 1_000_000
        output_cost = (out_m * profile["output_tokens"]) / 1_000_000
        raw_cost = input_cost + output_cost

    # Effective cost = raw cost / success rate
    success_rate = profile["success_rate"]
    effective = raw_cost / success_rate if success_rate > 0 else raw_cost

    return {
        "task": task,
        "task_description": profile["description"],
        "raw_cost_per_task": round(raw_cost, 6),
        "success_rate": success_rate,
        "effective_cost_per_task": round(effective, 6),
        "input_tokens": profile["input_tokens"],
        "output_tokens": profile["output_tokens"],
        "is_free": is_free,
    }


# --- The full scoring + badging pipeline ---

def score_and_badge(offer: dict, provider_meta: dict = None) -> dict:
    """Score an offer, derive badges, compute effective costs for all tasks."""
    vector = score_vector(offer, provider_meta)
    badges = derive_badges(vector, offer)

    # Effective costs for key tasks
    costs = {}
    for task in ["coding_task", "agentic_coding", "extraction", "chat_turn", "research_task"]:
        costs[task] = effective_cost_per_task(offer, task)

    return {
        **offer,
        "vector": vector,
        "badges": badges,
        "badge_labels": [BADGE_LABELS.get(b, b) for b in badges],
        "effective_costs": costs,
    }


def rank_by_dimension(offers: list[dict], dimension: str, limit: int = 20) -> list[dict]:
    """Rank offers by a specific scoring dimension."""
    scored = [score_and_badge(o) for o in offers]
    scored.sort(key=lambda x: x["vector"].get(dimension, 0), reverse=True)
    return scored[:limit]


def rank_by_badge(offers: list[dict], badge: str, limit: int = 20) -> list[dict]:
    """Get all offers with a specific badge, ranked by workhorse score."""
    scored = [score_and_badge(o) for o in offers]
    badged = [s for s in scored if badge in s["badges"]]
    badged.sort(key=lambda x: x["vector"]["workhorse"], reverse=True)
    return badged[:limit]


def recommend(offers: list[dict], task: str = "coding_task",
              role: str = "worker", priority: str = "value",
              min_context: int = 0, tool_calling: bool = False,
              budget: float = None, limit: int = 5) -> dict:
    """Task-first recommendation: "I have this job, what should I use?" """
    scored = [score_and_badge(o) for o in offers]

    # Filter
    if min_context:
        scored = [s for s in scored if (s.get("context_tokens") or 0) >= min_context]
    if tool_calling:
        scored = [s for s in scored if s["vector"]["tool_calling"] >= 60]
    if budget:
        scored = [s for s in scored if s["effective_costs"].get(task, {}).get("effective_cost_per_task", 999) <= budget]

    # Score for this specific task
    task_key = f"effective_cost_per_task"
    for s in scored:
        cost = s["effective_costs"].get(task, {}).get("effective_cost_per_task", 999)
        vec = s["vector"]
        # Task-specific composite
        if role == "worker":
            s["_task_score"] = vec["workhorse"] * 0.4 + vec["speed"] * 0.2 + (100 - min(100, cost * 1000)) * 0.4
        elif role == "planner":
            s["_task_score"] = vec["intelligence"] * 0.5 + vec["research"] * 0.3 + vec["agentic"] * 0.2
        elif role == "reviewer":
            s["_task_score"] = vec["intelligence"] * 0.4 + vec["coding"] * 0.4 + vec["reliability"] * 0.2
        else:
            s["_task_score"] = vec["workhorse"]

    scored.sort(key=lambda x: x.get("_task_score", 0), reverse=True)

    if not scored:
        return {"pick": None, "why": ["No models match your criteria"], "alternatives": {}}

    best = scored[0]
    return {
        "pick": best.get("model_id"),
        "provider": best.get("provider_id"),
        "vector": best["vector"],
        "badges": best["badges"],
        "why": _explain_pick(best, task, role),
        "effective_cost_per_task": best["effective_costs"].get(task, {}).get("effective_cost_per_task"),
        "alternatives": {
            "cheapest": scored[-1].get("model_id") if len(scored) > 1 else None,
            "fastest": max(scored, key=lambda x: x["vector"]["speed"]).get("model_id") if scored else None,
            "smartest": max(scored, key=lambda x: x["vector"]["intelligence"]).get("model_id") if scored else None,
        },
        "all_picks": [{"model": s.get("model_id"), "score": round(s.get("_task_score", 0), 1)} for s in scored[:limit]],
    }


def _explain_pick(offer: dict, task: str, role: str) -> list[str]:
    """Generate human-readable explanation for why this model was picked."""
    reasons = []
    vec = offer["vector"]
    badges = offer["badges"]

    if "workhorse" in badges: reasons.append("excellent workhorse")
    if "agentic" in badges: reasons.append("strong agentic capability")
    if "tool_caller" in badges: reasons.append("reliable tool calling")
    if "fast" in badges: reasons.append("fast inference")
    if offer.get("free"): reasons.append("free to use")
    if vec["value"] >= 80: reasons.append("exceptional value")
    if vec["intelligence"] >= 85: reasons.append("frontier intelligence")
    if vec["reliability"] >= 75: reasons.append("highly reliable")

    cost = offer["effective_costs"].get(task, {}).get("effective_cost_per_task", 0)
    if cost < 0.01: reasons.append(f"very low task cost (${cost:.4f})")
    elif cost < 0.10: reasons.append(f"low task cost (${cost:.2f})")

    return reasons[:4]  # top 4 reasons
