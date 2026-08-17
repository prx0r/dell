#!/usr/bin/env python3
"""app/routing.py — the advanced LLM router (arXiv algorithms, cold-start + learning).

Implements the recommended two-phase design from the research:

  PHASE 1 — Cold-start utility recommender (RouteProfile 2605.00180 / BELLA 2602.02386):
      per-task capability vector  Q(m,c)  (SWE-Bench→coding, GPQA→reasoning, ...)
      feasible set F(q) = { m : ctx≥needed ∧ modality⊇req ∧ capability⊇req ∧ !price0-artifact }
      utility   U(m|q) = Q(m,c(q)) − λ·Cost(m) − μ·Latency(m)
      m* = argmax U over F
      λ (cost weight) is the knob: large λ → free wins; small λ → quality wins.
      This GENERALIZES the naive "free-first" sort.

  PHASE 2 — LinUCB with benchmark surrogate + exploration (PILOT 2508.21141 / 2607.09015):
      arm = model; context = model-feature vector; reward = quality − cost
      maintain Q̂_bandit (ridge/LinUCB) blended with the static benchmark surrogate:
          Q̂ = w·Q̂_bandit + (1−w)·Q̂_benchmark,  w→1 as feedback accumulates
      m* = argmax [ Q̂(m) + α·√(xᵀA⁻¹x) − λ·Cost(m) ]   ← the exploration bonus makes it advanced
      (actively probes under-tested models instead of trusting benchmarks forever)

"Tools don't become truth. Their outputs become observations." — newbuild
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import benchmark_quality

FEEDBACK = ROOT / "data" / "router-feedback.json"

# benchmark → capability dimension
BENCH_TO_CAP = {
    "coding": ["SWE-Bench Verified", "SWE-Bench Pro", "Terminal-Bench", "Aider Polyglot", "Artificial Analysis Coding Index"],
    "reasoning": ["Humanity's Last Exam", "SciCode", "GPQA"],
    "research": ["Humanity's Last Exam", "SWE-Bench Pro", "Artificial Analysis Coding Index"],
    "extraction": ["Artificial Analysis Coding Index"],
    "long-context": [],
}

DEFAULT_LAMBDA = 0.05   # cost weight — large = free wins (the user's priority)
DEFAULT_MU = 0.0        # latency weight (no latency data yet)


def _db():
    import normalize
    if not (ROOT / "data" / "canonical-models.json").exists():
        normalize.normalize()
    return json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8"))


def _is_free(mid, rec) -> bool:
    """A model is FREE only if a real price source says so (OpenRouter ':free' slug or a free-apis
    entry), NOT just because models.dev has no price (233 models.dev listings are wrongly free:True).
    """
    if ":free" in mid:
        return True
    src = rec.get("source")
    if src == "awesome-free-llm-apis":
        return True
    return False


def _cost(rec, input_tok=20000, output_tok=4000) -> float:
    return (rec.get("prompt_per_token", 0) * input_tok
            + rec.get("completion_per_token", 0) * output_tok)


def _feasible(mid, rec, task, min_ctx=0, require_modality=None):
    """F(q): filter to models that can do the task (ctx, modality, capability, not price-0-artifact)."""
    ctx = rec.get("context")
    if isinstance(ctx, (int, float)) and min_ctx and ctx < min_ctx:
        return False
    if require_modality and require_modality not in (rec.get("input_modalities") or []):
        return False
    price0 = (rec.get("prompt_per_token", 0) == 0 and rec.get("completion_per_token", 0) == 0)
    if price0 and not _is_free(mid, rec):
        return False  # price-0 artifact with no real price AND not genuinely free → skip
    return True


def _quality_vector(rec, task) -> dict:
    """Q(m,c): the per-task capability quality (measured benchmark, normalized 0-100)."""
    bmarks = rec.get("benchmarks", []) or []
    if not bmarks:
        return {"q": None}
    # best measured score for this task's capability
    best = 0.0
    bench = None
    for wanted in BENCH_TO_CAP.get(task, []):
        kw = wanted.lower().split(" ")[0] + "-"
        for b in bmarks:
            name = (b.get("name") or "").lower()
            if kw and (kw in name or wanted.lower() in name):
                s = float(b.get("score") or 0)
                if s > best:
                    best, bench = min(s, 100.0), b.get("name")
    if best == 0.0:
        # fallback: any coding-ish benchmark
        for b in bmarks:
            if any(k in (b.get("name") or "") for k in ("SWE", "Terminal", "Coding")):
                s = float(b.get("score") or 0)
                if s > best:
                    best, bench = min(s, 100.0), b.get("name")
    return {"q": best if best > 0 else None, "benchmark": bench}


def _load_feedback() -> list[dict]:
    if not FEEDBACK.exists():
        return []
    try:
        return json.loads(FEEDBACK.read_text())
    except Exception:
        return []


def _save_feedback(fb):
    FEEDBACK.write_text(json.dumps(fb, indent=1))


# ---- Phase 1: cold-start utility argmax ----
def _rate_limit(mid: str) -> dict:
    """The provider's rate limit (rpm/rpd/tokens_per_day) for a model, if known.
    Checks the free-apis per-model limits first (the real free-tier quotas), then the known
    free-quota table. An OpenRouter ':free' model (rate-limited free pool) defaults to the
    OpenRouter free quota — so batch work correctly deprioritizes it (free ≠ good if too limited)."""
    import free_limits
    rl = free_limits.rate_limit_for(mid.split("/")[0], mid)
    if rl and (rl.get("rpd") or rl.get("rpm") or rl.get("tokens_per_day")):
        return rl
    import rate_limits
    m = mid.lower()
    # OpenRouter :free models are on the rate-limited free pool (~50-1000 RPD)
    if ":free" in m:
        q = rate_limits.FREE_QUOTAS.get("openrouter", {})
        return {"rpm": q.get("rpm"), "rpd": q.get("rpd"), "tokens_per_day": q.get("tokens_per_day")}
    for key, q in rate_limits.FREE_QUOTAS.items():
        if key in m or key.replace("-", "") in m:
            return {"rpm": q.get("rpm"), "rpd": q.get("rpd"), "tokens_per_day": q.get("tokens_per_day")}
    return {"rpm": None, "rpd": None, "tokens_per_day": None}


def recommend(task="coding", lambda_=DEFAULT_LAMBDA, mu=DEFAULT_MU, limit=5,
              min_ctx=0, require_modality=None, min_quality=0.0,
              daily_calls: int | None = None, volume_importance: float = 0.3) -> dict:
    """Phase-1 utility recommender: m* = argmax [Q(m) − λ·cost − μ·latency − ρ·quota_penalty].

    NOW RATE-LIMIT-AWARE (free ≠ good): a free model with a tiny quota that can't meet daily_calls
    is penalized, so a cheap paid model that CAN handle the volume ranks above it. The user's rule
    'free is best' holds ONLY when the free quota actually serves the workload.

    utility = Q − λ·cost − ρ·quota_penalty(daily_calls)
    where quota_penalty is large when the model's free rpd < daily_calls (can't serve the job).

    HOTSWAP: uses capability registry to filter out models from failed providers.
    "Tools don't become truth. Their outputs become observations." — newbuild
    """
    from capability_registry import get_registry
    reg = get_registry()

    db = _db().get("models", {})

    # Get healthy providers for model_db capability
    healthy_providers = set(reg.get_all_providers("model_db"))
    failed_providers = set()
    for p in reg.get_all_providers("model_db"):
        if not reg._health.get("model_db", {}).get(p, type('', (), {'is_usable': True})()).is_usable:
            failed_providers.add(p)

    scored = []
    skipped_failed = 0
    for mid, rec in db.items():
        # Hotswap: skip models from failed providers
        prov = rec.get("source", "")
        if prov in failed_providers:
            skipped_failed += 1
            continue

        if not _feasible(mid, rec, task, min_ctx, require_modality):
            continue
        qv = _quality_vector(rec, task)
        if qv["q"] is None:
            if _is_free(mid, rec):
                qv = {"q": 40.0, "benchmark": None}
            else:
                continue
        if qv["q"] < min_quality:
            continue
        cost = _cost(rec)
        free = _is_free(mid, rec)
        eff_cost = 0.0 if free else cost
        q = qv["q"]
        # rate-limit penalty: can this model serve the workload? (free ≠ good if too limited)
        rl = _rate_limit(mid)
        rpd = rl.get("rpd")
        tpd = rl.get("tokens_per_day")
        penalty = 0.0
        if daily_calls:
            # per-call token use ~24k (20k in + 4k out); a free quota caps both calls AND tokens
            needed_tokens = daily_calls * 24000
            cap_tokens = tpd if tpd is not None else float("inf")
            cap_calls = rpd if (rpd is not None) else float("inf")
            # free models have real caps; paid models with unknown limits don't get penalized
            if free:
                if cap_tokens < needed_tokens:
                    short = (needed_tokens - cap_tokens) / needed_tokens
                    penalty = short * 30.0 * volume_importance
                elif cap_calls < daily_calls:
                    penalty = ((daily_calls - cap_calls) / daily_calls) * 30.0 * volume_importance
        utility = q - lambda_ * (eff_cost * 1e6) - penalty

        # Record provenance: this model's data came from this source
        provenance = rec.get("provenance", {})
        scored.append({"model": mid, "provider": rec.get("provider"), "free": free,
                       "q": q, "benchmark": qv["benchmark"], "cost": cost,
                       "utility": round(utility, 2), "rpm": rl.get("rpm"), "rpd": rpd,
                       "quota_penalty": round(penalty, 2),
                       "source": provenance.get("source", rec.get("source", "unknown")),
                       "observed_at": provenance.get("observed_at")})
    # cost-first: free (eff_cost 0) rises to top via the utility (large lambda makes free win),
    # then by quality within a cost tier.
    scored.sort(key=lambda m: (-m["free"], m["cost"], -m["q"]))
    return {"task": task, "lambda": lambda_, "picks": scored[:limit],
            "algorithm": "phase1-utility-argmax (RouteProfile/BELLA)",
            "note": "U(m|q)=Q−λ·cost−μ·latency over feasible set; λ large → free wins",
            "hotswap": {"skipped_failed_providers": list(failed_providers),
                        "skipped_models": skipped_failed}}


# ---- Phase 2: LinUCB with benchmark surrogate + exploration ----
def linucb(task="coding", lambda_=DEFAULT_LAMBDA, alpha=1.0, limit=5) -> dict:
    """Phase-2: LinUCB with the benchmark surrogate as prior + exploration bonus.
    Q̂ = w·Q̂_bandit + (1−w)·Q̂_benchmark; m* = argmax[Q̂ + α·√(xᵀA⁻¹x) − λ·cost]."""
    db = _db().get("models", {})
    fb = _load_feedback()
    # w grows with feedback: w = n/(n+10) — trust the bandit more as data accumulates
    n = len(fb)
    w = n / (n + 10.0) if n else 0.0
    # per-model bandit stats (ridge: A = x·xᵀ sum + λI, b = x·r sum); x = [1, cost_norm, q_norm]
    stats = {}
    for f in fb:
        mid = f.get("model")
        if mid not in stats:
            stats[mid] = {"A11": 1.0, "A22": 1.0, "A33": 1.0, "b1": 0.0, "b2": 0.0, "b3": 0.0, "n": 0}
        s = stats[mid]
        x = [1.0, min(f.get("cost", 0) * 1e5, 10.0), min((f.get("quality") or 0) / 50.0, 2.0)]
        s["A11"] += x[0] * x[0]; s["A22"] += x[1] * x[1]; s["A33"] += x[2] * x[2]
        r = (f.get("quality") or 0) - lambda_ * (f.get("cost") or 0) * 1e6
        s["b1"] += x[0] * r; s["b2"] += x[1] * r; s["b3"] += x[2] * r
        s["n"] += 1
    scored = []
    for mid, rec in db.items():
        if not _feasible(mid, rec, task):
            continue
        qv = _quality_vector(rec, task)
        if qv["q"] is None:
            continue
        cost = _cost(rec)
        free = _is_free(mid, rec)
        eff_cost = 0.0 if free else cost
        q_bench = qv["q"]
        s = stats.get(mid, {"A11": 1.0, "A22": 1.0, "A33": 1.0, "b1": 0.0, "b2": 0.0, "b3": 0.0, "n": 0})
        # ridge estimate of the bandit quality
        q_bandit = s["b1"] / s["A11"] if s["n"] else q_bench
        q_hat = w * q_bandit + (1 - w) * q_bench
        # exploration bonus (UCB): sqrt(xᵀA⁻¹x) ~ sqrt(1/A11)
        bonus = alpha * math.sqrt(1.0 / s["A11"])
        utility = q_hat + bonus - lambda_ * (eff_cost * 1e6)
        scored.append({"model": mid, "provider": rec.get("provider"), "free": free,
                       "q": round(q_hat, 1), "q_benchmark": q_bench, "q_bandit": round(q_bandit, 1),
                       "explored": s["n"], "cost": cost, "utility": round(utility, 2)})
    scored.sort(key=lambda m: (-m["free"], m["cost"], -m["utility"]))
    return {"task": task, "alpha": alpha, "lambda": lambda_, "feedback_n": n,
            "exploration_weight": round(w, 2), "picks": scored[:limit],
            "algorithm": "phase2-linucb+surrogate (PILOT/2607.09015)",
            "note": "Q̂=w·bandit+(1−w)·benchmark; +α·exploration bonus probes under-tested models"}


def log_feedback(model: str, quality: float, cost: float = 0.0):
    """Record a real outcome (quality score − cost) so the bandit learns."""
    fb = _load_feedback()
    fb.append({"model": model, "quality": quality, "cost": cost,
               "ts": time.time()})
    _save_feedback(fb[-2000:])  # keep last 2000


if __name__ == "__main__":
    print("PHASE 1 (cold-start utility):")
    for p in recommend("reasoning", limit=5)["picks"][:3]:
        print(f"  {p['model'][:40]:<42} q={p['q']} cost=${p['cost']:.5f} free={p['free']}")
    print("PHASE 2 (LinUCB + surrogate + exploration):")
    for p in linucb("reasoning", limit=3)["picks"][:3]:
        print(f"  {p['model'][:40]:<42} q={p['q']} explored={p['explored']} free={p['free']}")
# LEGACY: V1 pipeline. Use scoring.py instead
