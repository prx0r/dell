#!/usr/bin/env python3
"""agent/run.py — the AGENT-RUN orchestrator for dealradar.

A single entry point an agent (or the watchdog) calls to run ANY dealradar step, kanban-aware:
  - runs the underlying module (refresh / canary / validate / normalize / recommend / route)
  - logs the result to the agent-runs registry
  - content-addresses the result (run recorder — the provenance ledger)

Designed to be driven by hermes (kanban + skill) OR by cron (watchdog).

Usage:
  python3 agent/run.py --step validate                 # run all tests (the gate)
  python3 agent/run.py --step normalize                # rebuild the canonical model DB
  python3 agent/run.py --step refresh                  # check live prices + drift
  python3 agent/run.py --step canary                   # probe the free providers (live)
  python3 agent/run.py --step recommend --task coding --prefer-free
  python3 agent/run.py --step report                   # the model-count + health summary
  python3 agent/run.py --step watchdog                 # refresh → canary → validate → report
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT))


def _sh(*args: str, timeout: int = 900) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return f"__TIMEOUT__ {' '.join(args)}"


def _log(record: dict) -> None:
    reg = ROOT / "data" / "agent-runs.jsonl"
    reg.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with open(reg, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    # also append to the centralized agent-steps trace (the anti-mess ledger)
    step_reg = ROOT / "data" / "runs" / "agent-steps.jsonl"
    step_reg.parent.mkdir(parents=True, exist_ok=True)
    with open(step_reg, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def step_validate() -> dict:
    out = _sh("python3", str(ROOT / "app" / "test.py"), timeout=300)
    rec = {"step": "validate", "output": out[-2000:]}
    _log(rec)
    print(out)
    return rec


def step_normalize() -> dict:
    import normalize
    m = normalize.normalize()
    n = len(m) if isinstance(m, (dict, list)) else 0
    rec = {"step": "normalize", "models": n, "output": f"{n} canonical models"}
    _log(rec)
    print(f"canonical models: {n}")
    return rec


def step_refresh() -> dict:
    import refresh
    out = refresh.main() if hasattr(refresh, "main") else str(refresh.check())
    rec = {"step": "refresh", "output": str(out)[-2000:]}
    _log(rec)
    print(out)
    return rec


def step_canary() -> dict:
    import canary
    out = canary.main() if hasattr(canary, "main") else str(canary.check())
    rec = {"step": "canary", "output": str(out)[-2000:]}
    _log(rec)
    print(out)
    return rec


def step_recommend(task: str, min_quality: float, daily_calls: int | None) -> dict:
    import routing
    res = routing.recommend(task=task, min_quality=min_quality, daily_calls=daily_calls)
    rec = {"step": "recommend", "task": task, "min_quality": min_quality,
           "daily_calls": daily_calls,
           "output": json.dumps(res, ensure_ascii=False)[-2000:]}
    _log(rec)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:2000])
    return rec


def step_report() -> dict:
    import normalize
    m = normalize.normalize()
    items = list(m.values()) if isinstance(m, dict) else (m if isinstance(m, list) else [])
    free = [x for x in items if isinstance(x, dict) and x.get("free")]
    rec = {"step": "report", "models": len(items), "free": len(free),
           "output": f"{len(items)} models, {len(free)} free"}
    _log(rec)
    print(f"canonical: {len(items)} models | {len(free)} free-tier")
    return rec


def step_watchdog() -> dict:
    print(f"=== WATCHDOG {datetime.now(timezone.utc).isoformat()} ===")
    r = step_report()
    c = step_canary()
    v = step_validate()
    _log({"step": "watchdog", "models": r.get("models"), "canary": c.get("output", "")[-200:]})
    return r


def _run_module(name: str, fn: str = "", arg: str = "") -> dict:
    """Run a dealradar module's entry (or a generic call) + log it."""
    import importlib
    out = ""
    try:
        mod = importlib.import_module(name)
        if fn and hasattr(mod, fn):
            out = str(getattr(mod, fn)(arg)) if arg else str(getattr(mod, fn)())
        else:
            out = f"(module {name} has no {fn or 'self-test'})"
    except Exception as e:
        out = f"__ERROR__ {e}"
    rec = {"step": name, "output": out[-2000:]}
    _log(rec)
    print(out)
    return rec


def step_tensions() -> dict:
    return _run_module("tensions")


def step_layer() -> dict:
    return _run_module("layer_recommend", "recommend_layer", "L2")


def step_compute_sources() -> dict:
    return _run_module("compute_sources")


def step_rate_limits() -> dict:
    return _run_module("rate_limits")


def step_benchmark_quality() -> dict:
    return _run_module("benchmark_quality")


def step_task_ranking() -> dict:
    return _run_module("task_ranking")


def step_model_data() -> dict:
    return _run_module("model_data")


def step_advanced_query() -> dict:
    return _run_module("advanced_query")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True,
                    choices=["validate", "normalize", "refresh", "canary", "recommend", "report", "watchdog",
                             "tensions", "layer", "compute_sources", "rate_limits", "benchmark_quality",
                             "task_ranking", "model_data", "advanced_query"])
    ap.add_argument("--task", default="coding")
    ap.add_argument("--min-quality", type=float, default=0.0)
    ap.add_argument("--daily-calls", type=int, default=None)
    args = ap.parse_args()
    simple = {"validate": step_validate, "normalize": step_normalize, "refresh": step_refresh,
              "canary": step_canary, "report": step_report, "watchdog": step_watchdog,
              "tensions": step_tensions, "layer": step_layer, "compute_sources": step_compute_sources,
              "rate_limits": step_rate_limits, "benchmark_quality": step_benchmark_quality,
              "task_ranking": step_task_ranking, "model_data": step_model_data,
              "advanced_query": step_advanced_query}
    if args.step == "recommend":
        step_recommend(args.task, args.min_quality, args.daily_calls)
    else:
        simple[args.step]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
