#!/usr/bin/env python3
"""app/task_ranking.py — the task-aware agent-performance sorting engine.

Applies the agent-performance logic (eigenius D50 + mcp-eval) to MODEL SELECTION. Instead of ranking
by $/M tokens or a single quality number, rank by PER-TASK agent performance:

    headline = success_rate × quality  /  (effective_cost × latency)

with a per-axis breakdown, so an agent can answer "what's the best model for THIS task type" —
coding / research / extraction / long-context / reasoning — instantly.

Task profiles weight the quality axes differently (the eigenius per-condition comparison idea):
  coding      → quality.coding heavy, success on long tool calls
  research    → intelligence + agentic
  extraction  → cheap + reliable (success matters more than peak quality)
  long-context→ context length + cost (cheap per token at big context)
  reasoning   → intelligence heavy
Each model gets a TASK-SPECIFIC score. This is the "useful sorting algorithm for an AI."
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))
DB = ROOT / "data" / "canonical-models.json"

# task → per-axis weights + success baseline + latency sensitivity
TASK_PROFILES = {
    "coding":      {"coding": 0.5, "agentic": 0.25, "intelligence": 0.25, "success": 0.90, "latency_w": 0.3, "min_ctx": 0},
    "research":    {"coding": 0.2, "agentic": 0.35, "intelligence": 0.45, "success": 0.85, "latency_w": 0.2, "min_ctx": 0},
    "extraction":  {"coding": 0.2, "agentic": 0.30, "intelligence": 0.50, "success": 0.97, "latency_w": 0.4, "min_ctx": 0},
    "long-context": {"coding": 0.25, "agentic": 0.3, "intelligence": 0.45, "success": 0.80, "latency_w": 0.1, "min_ctx": 128000},
    "reasoning":   {"coding": 0.15, "agentic": 0.4, "intelligence": 0.45, "success": 0.85, "latency_w": 0.2, "min_ctx": 0},
}
DEFAULT_TASK = "coding"
TASKS = list(TASK_PROFILES)


def _ctx(rec) -> int:
    c = rec.get("context")
    if isinstance(c, (int, float)):
        return int(c)
    if isinstance(c, str):
        try:
            return int(c.replace(",", "").replace("k", "000"))
        except ValueError:
            return 0
    return 0


def task_score(rec: dict, quality: dict, task: str = DEFAULT_TASK) -> dict:
    """The agent-performance score for ONE model on ONE task. Per-axis breakdown."""
    prof = TASK_PROFILES.get(task, TASK_PROFILES[DEFAULT_TASK])
    ctx = _ctx(rec)
    if prof["min_ctx"] and ctx and ctx < prof["min_ctx"]:
        return {"eligible": False, "reason": f"context {ctx} < {prof['min_ctx']} required", "score": 0.0}
    q = (quality.get("coding", 60) * prof["coding"]
         + quality.get("agentic", 55) * prof["agentic"]
         + quality.get("intelligence", 58) * prof["intelligence"])
    cost = (rec.get("prompt_per_token", 0) * 20000 + rec.get("completion_per_token", 0) * 4000)
    # effective cost penalized by success (a model that fails needs retries)
    success = prof["success"]
    eff_cost = cost / success if success > 0 else 0
    # latency sensitivity (no real latency data yet → 1.0 neutral)
    latency_factor = 1.0
    # the headline: quality × success / (effective cost × latency)
    if eff_cost > 0:
        score = (q / 100.0) * success / (eff_cost * latency_factor)
        score = min(score, 10000.0)  # cap so free models don't produce absurd 1e11 scores
    else:
        # a genuinely free model: score by quality × success (no cost denominator), capped
        score = min((q / 100.0) * success * 10000.0, 10000.0)
    return {"eligible": True, "score": round(score, 2), "task_quality": round(q, 1),
            "cost_per_task": round(cost, 8), "effective_cost": round(eff_cost, 8),
            "success_rate": success, "context": ctx}


def rank(models: dict, aa_quality: dict, task: str = DEFAULT_TASK,
         min_quality: float = 0.0, prefer_free: bool = False, limit: int = 10,
         exclude: tuple = ("embedding", "audio", "image", "tts", "stt", "whisper",
                           "stable-diffusion", "flux", "dall-e", "sdxl", "/e5-", "bge-",
                           "rerank", "colbert", "ollama/", "sample_spec", "bedrock/",
                           "ssd-1b", "playground", "1024", "canvas", "nova-canvas",
                           "img", "video")):
    """Rank all models for a task, sorted by the agent-performance headline score."""
    from quality import quality_for
    scored = []
    for mid, rec in models.items():
        low = mid.lower()
        if any(x in low for x in exclude):
            continue
        if "embedding" in (rec.get("provider") or "").lower():
            continue
        if rec.get("prompt_per_token", 0) == 0 and rec.get("completion_per_token", 0) == 0 and not rec.get("free"):
            continue
        q = aa_quality.get(mid) or quality_for(mid, rec.get("provider", ""))
        if isinstance(q, dict) and "scores" not in q:
            q = {"scores": q, "source": "measured"}
        ts = task_score(rec, q.get("scores", {}), task)
        if not ts["eligible"]:
            continue
        qq = ts["task_quality"]
        if min_quality and qq < min_quality:
            continue
        is_free = rec.get("free", False) or (rec.get("prompt_per_token", 0) == 0 and rec.get("completion_per_token", 0) == 0)
        if prefer_free and not is_free:
            continue
        scored.append({"model": mid, "provider": rec.get("provider"), "free": is_free,
                       "quality_source": q.get("source", "estimated"), **ts})
    scored.sort(key=lambda s: -s["score"])
    return scored[:limit]


def task_summary(task: str = DEFAULT_TASK) -> dict:
    """The per-task leaderboard (headline comparison, like eigenius §6.4)."""
    db = json.loads(DB.read_text(encoding="utf-8"))
    return {"task": task, "ranking": rank(db.get("models", {}), {}, task=task)}


if __name__ == "__main__":
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK
    for m in task_summary(task)["ranking"][:5]:
        print(f"  {m['model'][:44]:<46} task_q={m['task_quality']} score={m['score']} "
              f"cost/task=${m['cost_per_task']:.6f} ctx={m['context']}")
# LEGACY: V1 pipeline. Use scoring.py instead
