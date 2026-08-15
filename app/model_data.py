#!/usr/bin/env python3
"""app/model_data.py — the LLM-facing model-data API (data structure, not routing decisions).

The key insight: the LLM using the MCP does the REASONING. So Python's job is to serve the COMPLETE,
honest data structure for each model — price, free-status, context, modalities, capabilities, measured
benchmarks, license, open_weights, rate-limits — and let the LLM weigh cost vs quality vs batch vs
interactive itself.

This exposes:
  full_record(model)      → every field for one model (the LLM reasons over it)
  search(filters)         → models matching task/modality/free/price, with full records
  free_pool_summary()     → the free sources + their rate limits (for batch-vs-interactive reasoning)
  compare(models)         → side-by-side full records for the LLM to compare

No over-deciding here: Python filters + serves data; the LLM picks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import rate_limits
import compute_sources


def _db():
    import normalize
    if not (ROOT / "data" / "canonical-models.json").exists():
        normalize.normalize()
    return json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8"))


def _is_free(mid, rec) -> bool:
    return ":free" in mid or rec.get("source") == "awesome-free-llm-apis"


def full_record(model: str) -> dict:
    """Every field for one model — the data the LLM reasons over."""
    db = _db().get("models", {})
    rec = db.get(model)
    if not rec:
        base = model.split("/")[-1].lower()
        for mid, r in db.items():
            if len(base) >= 4 and base in mid.lower():
                rec, model = r, mid
                break
    if not rec:
        return {"error": f"model {model} not found"}
    free = _is_free(model, rec)
    # per-task measured quality (best benchmark score per task)
    tasks = {}
    for task, benchs in [("coding", ["SWE-Bench", "Terminal-Bench", "Aider", "Coding"]),
                         ("reasoning", ["GPQA", "Humanity's Last Exam", "SciCode"]),
                         ("research", ["Humanity's Last Exam", "SWE-Bench", "Coding"])]:
        best = max((b.get("score") for b in (rec.get("benchmarks") or [])
                    if any(k in (b.get("name") or "") for k in benchs)), default=None)
        if best:
            tasks[task] = round(float(best), 1)
    # cost per task (20k in / 4k out)
    cost = (rec.get("prompt_per_token", 0) * 20000 + rec.get("completion_per_token", 0) * 4000)
    # the provider's rate limit (for batch reasoning)
    prov = model.split("/")[0].lower()
    quota = {}
    for key, q in rate_limits.FREE_QUOTAS.items():
        if key in prov or prov in key:
            quota = q
            break
    return {
        "model": model, "provider": rec.get("provider"),
        "price": {"prompt_per_token": rec.get("prompt_per_token"),
                  "completion_per_token": rec.get("completion_per_token"),
                  "cache_read_per_token": rec.get("cache_read_per_token"),
                  "cost_per_task_approx": round(cost, 6)},
        "free": free, "context": rec.get("context"),
        "modalities": {"input": rec.get("input_modalities", []), "output": rec.get("output_modalities", [])},
        "capabilities": {"reasoning": rec.get("reasoning"), "tool_call": rec.get("tool_call"),
                         "structured_output": rec.get("structured_output")},
        "measured_quality": tasks,   # per-task benchmark scores (the LLM uses these)
        "license": rec.get("license"), "open_weights": rec.get("open_weights"),
        "provider_rate_limit": quota,  # rpm/rpd/tokens-per-day if known
        "source": rec.get("source"),
    }


def search(task: str | None = None, modality: str | None = None, free_only: bool = False,
           max_cost: float | None = None, min_quality: float = 0.0, limit: int = 10) -> dict:
    """Filter models and return FULL records for each (the LLM compares them itself)."""
    db = _db().get("models", {})
    out = []
    for mid, rec in db.items():
        if not _is_free(mid, rec) and (rec.get("prompt_per_token", 0) == 0 and rec.get("completion_per_token", 0) == 0):
            continue  # price-0 non-free artifact
        if free_only and not _is_free(mid, rec):
            continue
        if modality and modality not in (rec.get("input_modalities") or []):
            continue
        cost = (rec.get("prompt_per_token", 0) * 20000 + rec.get("completion_per_token", 0) * 4000)
        if max_cost is not None and cost > max_cost:
            continue
        rec_full = full_record(mid)
        if task:
            q = (rec_full.get("measured_quality") or {}).get(task)
            if q is None or q < min_quality:
                continue
        out.append(rec_full)
    # sort: free first, then by cost, then by the task quality if given
    out.sort(key=lambda r: (not r["free"], r["price"]["cost_per_task_approx"],
                            -(r.get("measured_quality") or {}).get(task, 0) if task else 0))
    return {"count": len(out), "results": out[:limit]}


def compare(models: list[str]) -> dict:
    """Side-by-side full records for comparison."""
    return {"models": [full_record(m) for m in models]}


def free_pool_summary() -> dict:
    """The free sources + rate limits — the data the LLM needs for batch-vs-interactive reasoning."""
    return {"free_pool": compute_sources.free_pool(), "rate_limits": rate_limits.all_rate_limits()}


if __name__ == "__main__":
    import sys as _s
    q = _s.argv[1] if len(_s.argv) > 1 else "image"
    r = search(modality="image", limit=3)
    print(f"image models: {r['count']}")
    for m in r["results"][:3]:
        print(f"  {m['model'][:40]:<42} free={m['free']} cost=${m['price']['cost_per_task_approx']:.5f} ctx={m['context']}")
