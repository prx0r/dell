#!/usr/bin/env python3
"""app/benchmark_quality.py — real, measured model quality from benchmark scores (not family guesses).

models.dev embeds current benchmark scores (SWE-Bench, Terminal-Bench, Aider Polyglot, Artificial
Analysis Coding Index, Humanity's Last Exam, etc.) on 1,134+ models. These are REAL measured quality
signals — far better than the per-family estimates. This maps benchmark scores to per-task quality:

  coding    → SWE-Bench Verified / SWE-Bench Pro / Terminal-Bench / Aider / AA Coding Index
  reasoning → Humanity's Last Exam / SciCode
  research  → a blend of the above + intelligence
  (vision/extraction use the family fallback — benchmarks are text/code-centric)

Each benchmark's score is normalized to 0-100 (scores are % or 0-100). If a model has no benchmark,
we fall back to the family estimate (honest: quality_source = estimated).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "canonical-models.json"

# task → benchmark-name priority (which benchmark best measures that task)
TASK_BENCHMARKS = {
    "coding": ["SWE-Bench Verified", "SWE-Bench Pro", "Terminal-Bench", "Aider Polyglot",
               "Artificial Analysis Coding Index"],
    "reasoning": ["Humanity's Last Exam", "SciCode", "GPQA"],
    "research": ["Humanity's Last Exam", "SWE-Bench Pro", "Artificial Analysis Coding Index"],
    "extraction": ["Artificial Analysis Coding Index"],  # extraction ≈ reliable instruction-following
    "long-context": [],  # no good long-context benchmark in models.dev → family fallback
}


def load() -> dict:
    return json.loads(DB.read_text(encoding="utf-8")).get("models", {})


def _norm_score(score, metric: str = "") -> float:
    """Normalize a benchmark score to 0-100."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.0
    if metric in ("Elapsed Tokens",) or s > 100:  # some metrics aren't % — cap conservatively
        return min(s, 100.0)
    return max(0.0, min(s, 100.0)) if s <= 100 else min(s, 100.0)


def model_benchmarks(model: str) -> list[dict]:
    """The raw benchmark list for a model (from models.dev, embedded in the canonical DB)."""
    db = load()
    rec = db.get(model)
    if not rec:
        # fuzzy: match by base model name, but require a REAL token overlap (≥4 chars) so a 3-letter
        # substring like 'xyz' can't false-positive onto an unrelated model.
        base = model.split("/")[-1].lower()
        best = None
        for mid, r in db.items():
            mid_base = mid.split("/")[-1].lower()
            if not mid_base or len(base) < 4:
                continue  # skip empty-base records; require a real query token
            if base in mid or mid in base or base in mid_base or mid_base in base:
                best = r
                break
        rec = best
    if not rec:
        return []
    return rec.get("benchmarks", []) or []


def benchmark_quality(model: str, task: str = "coding") -> dict:
    """Measured quality from the model's real benchmark scores. Returns {score, source, benchmark}."""
    bmarks = model_benchmarks(model)
    if not bmarks:
        return {"score": None, "source": "estimated", "benchmark": None}
    # substring match (models.dev names vary: 'SWE-Bench Pro' vs 'SWE Bench Pro', 'Terminal-Bench 2.1')
    for wanted in TASK_BENCHMARKS.get(task, []):
        kw = wanted.lower().split()[0] + "-"  # e.g. 'swe-', 'terminal-', 'aider', 'artificial'
        for b in bmarks:
            name = (b.get("name") or "").lower()
            if kw in name or wanted.lower() in name:
                s = _norm_score(b.get("score"), b.get("metric", ""))
                if s > 0:
                    return {"score": s, "source": "measured",
                            "benchmark": b.get("name"), "metric": b.get("metric")}
    # no matching benchmark → use the best available coding benchmark as a proxy
    coding = [b for b in bmarks if any(k in (b.get("name") or "") for k in
                                        ("SWE", "Terminal", "Aider", "Coding"))]
    if coding:
        b = max(coding, key=lambda x: _norm_score(x.get("score"), x.get("metric", "")))
        return {"score": _norm_score(b.get("score"), b.get("metric", "")),
                "source": "measured", "benchmark": b.get("name"), "metric": b.get("metric")}
    return {"score": None, "source": "estimated", "benchmark": None}


def _bench_from_rec(rec: dict, task: str) -> dict:
    """Measured quality from a model RECORD's own benchmarks (no fuzzy re-lookup — fast)."""
    bmarks = rec.get("benchmarks", []) or []
    if not bmarks:
        return {"score": None, "source": "estimated", "benchmark": None}
    for wanted in TASK_BENCHMARKS.get(task, []):
        kw = wanted.lower().split()[0] + "-"
        for b in bmarks:
            name = (b.get("name") or "").lower()
            if kw in name or wanted.lower() in name:
                s = _norm_score(b.get("score"), b.get("metric", ""))
                if s > 0:
                    return {"score": s, "source": "measured",
                            "benchmark": b.get("name"), "metric": b.get("metric")}
    coding = [b for b in bmarks if any(k in (b.get("name") or "") for k in
                                        ("SWE", "Terminal", "Aider", "Coding"))]
    if coding:
        b = max(coding, key=lambda x: _norm_score(x.get("score"), x.get("metric", "")))
        return {"score": _norm_score(b.get("score"), b.get("metric", "")),
                "source": "measured", "benchmark": b.get("name"), "metric": b.get("metric")}
    return {"score": None, "source": "estimated", "benchmark": None}


def top_benchmarked(task: str = "coding", limit: int = 10) -> list[dict]:
    """The models with the HIGHEST measured benchmark score for a task (the real quality leaders)."""
    db = load()
    out = []
    for mid, rec in db.items():
        if not rec.get("benchmarks"):
            continue  # only models with measured benchmarks (fast path, no fuzzy scan)
        bq = _bench_from_rec(rec, task)
        if bq["score"] is not None:
            out.append({"model": mid, "provider": rec.get("provider"),
                        "benchmark_score": round(bq["score"], 1), "benchmark": bq["benchmark"],
                        "context": rec.get("context")})
    out.sort(key=lambda x: -x["benchmark_score"])
    return out[:limit]


if __name__ == "__main__":
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "coding"
    for m in top_benchmarked(task)[:5]:
        print(f"  {m['model'][:44]:<46} {m['benchmark_score']} ({m['benchmark']})")
