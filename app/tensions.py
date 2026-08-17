#!/usr/bin/env python3
"""app/tensions.py — the multi-dimensional tension engine (the moat).

Beyond "free vs paid", a user actually weighs several TENSIONS when choosing a model:
  cost        — cheap per task (free = 1.0, expensive = low)
  quality     — measured benchmark score for the task
  rate_limit  — can it serve the daily volume? (high rpd/tpd = 1.0)
  latency     — fast vs slow (reasoning models are slower)
  context     — long-context capability
  reasoning   — reasoning-capable
  tools       — tool-call / structured-output capability
  open_weights— self-hostable + license freedom
  cache       — prompt-cache discount (repeated calls cheaper)

Each model gets a 0-1 score per tension. A USE-CASE PROFILE assigns weights to the tensions
(e.g. 'interactive' weights latency+quality; 'batch' weights cost+rate_limit; 'self-host'
weights open_weights; 'vision' weights modality). The weighted sum is the final score.

This gives the LLM the algorithm's multi-dimensional reasoning — it sees the tension scores +
the profile, and can weigh further itself. Not a single "free wins" — a real trade-off surface.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import routing
import free_limits
import rate_limits


def _is_free(mid, rec) -> bool:
    return ":free" in mid or rec.get("source") == "awesome-free-llm-apis"


def _quality_for(rec, task) -> float:
    bmarks = rec.get("benchmarks", []) or []
    if not bmarks:
        return 40.0 if _is_free("", rec) else 0.0
    best = 0.0
    for wanted in routing.BENCH_TO_CAP.get(task, []) + ["SWE", "Coding", "GPQA"]:
        kw = wanted.lower().split(" ")[0] + "-"
        for b in bmarks:
            name = (b.get("name") or "").lower()
            if kw and (kw in name or wanted.lower() in name):
                best = max(best, min(float(b.get("score") or 0), 100.0))
    return best if best > 0 else 40.0


def score_tensions(mid: str, rec: dict, task: str) -> dict:
    """Every tension as a 0-1 score for one model."""
    cost = routing._cost(rec)
    free = _is_free(mid, rec)
    # a price-0 NON-free artifact is un-priced, not cheap — don't give it a free cost score
    price0_artifact = (not free and rec.get("prompt_per_token", 0) == 0 and rec.get("completion_per_token", 0) == 0)
    eff_cost = 0.0 if free else cost
    # cost: free = 1.0; paid decays with price; a price-0 artifact gets a neutral 0.4 (un-priced, unclear)
    if price0_artifact:
        cost_score = 0.4
    else:
        cost_score = 1.0 if free else max(0.0, 1.0 - (eff_cost * 1e6) / 300.0)
    # quality (measured benchmark, normalized)
    q = _quality_for(rec, task)
    quality_score = q / 100.0
    # rate limit: can it serve a big daily volume? (from free_limits + openrouter :free default)
    rl = routing._rate_limit(mid)
    rpd = rl.get("rpd")
    tpd = rl.get("tokens_per_day")
    # ~1000 calls/day or 100M tokens/day = full capacity; lower = less
    calls_cap = rpd if rpd is not None else (1000 if free else 100000)
    tokens_cap = tpd if tpd is not None else (1e8 if not free else 5e6)
    rate_score = min(1.0, calls_cap / 1000.0) * min(1.0, tokens_cap / 1e8)
    # context: 128k+ = 1.0, scales down
    ctx = rec.get("context")
    ctx_score = 1.0 if isinstance(ctx, (int, float)) and ctx >= 128000 else \
        (max(0.0, float(ctx) / 128000.0) if isinstance(ctx, (int, float)) else 0.3)
    # reasoning / tools / structured
    reasoning_score = 1.0 if rec.get("reasoning") else 0.3
    tools_score = (1.0 if rec.get("tool_call") else 0.3) * (1.0 if rec.get("structured_output") else 0.7)
    # open weights / license
    open_score = 1.0 if rec.get("open_weights") else 0.0
    # cache discount (repeated calls cheaper)
    cache = rec.get("cache_read_per_token") or 0
    cache_score = min(1.0, (1.0 - cache / (rec.get("prompt_per_token", 1) * 0.5)) if rec.get("prompt_per_token") else 0.5)
    # latency proxy: reasoning models are slower → lower latency score
    latency_score = 0.5 if rec.get("reasoning") else 1.0
    return {"cost": round(cost_score, 2), "quality": round(quality_score, 2),
            "rate_limit": round(rate_score, 2), "context": round(ctx_score, 2),
            "reasoning": reasoning_score, "tools": round(tools_score, 2),
            "open_weights": open_score, "cache": round(cache_score, 2),
            "latency": latency_score, "rpd": rpd, "tokens_per_day": tpd}


# use-case profiles: tension → weight (how much this use-case cares)
PROFILES = {
    "interactive": {"quality": 1.0, "latency": 0.8, "cost": 0.5, "rate_limit": 0.3, "context": 0.4,
                    "reasoning": 0.6, "tools": 0.6, "open_weights": 0.0, "cache": 0.3},
    "batch": {"cost": 1.0, "rate_limit": 1.0, "quality": 0.6, "cache": 0.8, "context": 0.5,
              "reasoning": 0.3, "tools": 0.4, "latency": 0.2, "open_weights": 0.0},
    "quality": {"quality": 1.0, "reasoning": 1.0, "tools": 0.8, "context": 0.7, "latency": 0.3,
                "cost": 0.3, "rate_limit": 0.4, "open_weights": 0.0, "cache": 0.3},
    "self-host": {"open_weights": 1.0, "cost": 0.9, "context": 0.6, "quality": 0.6, "reasoning": 0.5,
                  "tools": 0.5, "latency": 0.5, "rate_limit": 0.0, "cache": 0.3},
    "cheap": {"cost": 1.0, "rate_limit": 0.8, "quality": 0.4, "cache": 0.5, "context": 0.3,
              "reasoning": 0.2, "tools": 0.3, "latency": 0.4, "open_weights": 0.2},
    "balanced": {"cost": 0.6, "quality": 0.8, "rate_limit": 0.6, "context": 0.6, "reasoning": 0.6,
                 "tools": 0.6, "latency": 0.5, "open_weights": 0.2, "cache": 0.4},
}


def score_model(mid: str, rec: dict, task: str, profile: str = "balanced") -> dict:
    """A model's tension scores + the profile-weighted total."""
    t = score_tensions(mid, rec, task)
    w = PROFILES.get(profile, PROFILES["balanced"])
    total = sum(t[k] * w[k] for k in w if k in t)
    denom = sum(w.values())
    return {"model": mid, "provider": rec.get("provider"), "free": _is_free(mid, rec),
            "cost_per_task": round(routing._cost(rec), 6),
            "tensions": {k: v for k, v in t.items() if k not in ("rpd", "tokens_per_day")},
            "rpd": t["rpd"], "tokens_per_day": t["tokens_per_day"],
            "profile": profile, "score": round(total / denom, 3)}


def recommend(task="coding", profile="balanced", limit=10, min_ctx=0, require_modality=None) -> dict:
    """Rank models by the profile-weighted tension score."""
    db = json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8")).get("models", {})
    scored = []
    for mid, rec in db.items():
        if not routing._feasible(mid, rec, task, min_ctx, require_modality):
            continue
        price0_artifact = (not _is_free(mid, rec) and rec.get("prompt_per_token", 0) == 0
                           and rec.get("completion_per_token", 0) == 0)
        if price0_artifact:
            continue  # un-priced non-free artifact — can't rank it honestly
        if not rec.get("benchmarks") and not _is_free(mid, rec):
            continue  # paid unbenchmarked → can't justify
        scored.append(score_model(mid, rec, task, profile))
    scored.sort(key=lambda s: -s["score"])
    return {"task": task, "profile": profile, "picks": scored[:limit],
            "profiles": list(PROFILES), "algorithm": "multi-dimensional-tension-utility"}


if __name__ == "__main__":
    import sys as _s
    prof = _s.argv[1] if len(_s.argv) > 1 else "balanced"
    task = _s.argv[2] if len(_s.argv) > 2 else "coding"
    r = recommend(task=task, profile=prof, limit=5)
    print(f"profile={prof} task={task}")
    for p in r["picks"][:5]:
        t = p["tensions"]
        print(f"  {p['model'][:32]:<34} score={p['score']} free={p['free']} "
              f"[cost={t['cost']} q={t['quality']} rate={t['rate_limit']} ctx={t['context']} open={t['open_weights']}]")
# LEGACY: V1 pipeline. Use scoring.py instead
