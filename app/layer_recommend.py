#!/usr/bin/env python3
"""app/layer_recommend.py — recommend the best free/cheap model for EACH translation layer.

Integrates the deal-radar with the other agent's per-layer translation stack. The stack runs each
translation layer (L0/T1/ARGMAP/L2/L200/C1) as its own stage with its own model (HERMES_MODEL per
worker). This maps each layer to a deal-radar TASK and auto-loads the best model for that layer's
character:

  T1     rough translation, high-volume batch  → extraction/coding  (cheap, reliable, big quota)
  ARGMAP 4-section structural outline          → reasoning          (structure + analysis)
  L2     guided philosophic prose              → research/writing    (prose quality)
  L200   8-section bounded audit               → reasoning           (bounded classifier)
  C1     scholarly commentary                  → research            (depth + accuracy)

Each layer can prefer_free (try free/cheap first) or prefer_quality (a strong model for hard layers).
Output includes WHY it was chosen (measured quality + cost + task fit) so the worker can log it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "app") not in sys.path:
    sys.path.insert(0, str(ROOT / "app"))

import task_ranking
import quality
import benchmark_quality

# layer → (task, default preference, why)
LAYER_MAP = {
    "T1":     {"task": "extraction", "prefer_free": True,  "why": "high-volume rough batch — cheap + reliable + big free quota"},
    "ARGMAP": {"task": "reasoning",  "prefer_free": False, "why": "needs structural analysis — a reasoning-capable model"},
    "L2":     {"task": "research",   "prefer_free": False, "why": "guided philosophic prose — writing quality matters"},
    "L200":   {"task": "reasoning",  "prefer_free": False, "why": "8-section bounded audit — needs careful reasoning"},
    "C1":     {"task": "research",   "prefer_free": False, "why": "scholarly commentary — depth + accuracy"},
    "L0":     {"task": None,         "prefer_free": True,  "why": "DETERMINISTIC (Vidyut) — no model needed"},
    "L1":     {"task": None,         "prefer_free": True,  "why": "DETERMINISTIC scaffold — no model needed"},
}


def recommend_layer(layer: str, limit: int = 3, force_task: str | None = None) -> dict:
    """The best models for a translation layer, ranked COST-FIRST then VALUE (via the routing module,
    which correctly handles free models + price-0 artifacts):
      1. genuinely-free models always win (you literally gain from them)
      2. then paid models by value (quality / cost)
    """
    spec = LAYER_MAP.get(layer.upper())
    if not spec:
        return {"error": f"unknown layer {layer}; use {list(LAYER_MAP)}"}
    task = force_task or spec["task"]
    if not task:
        return {"layer": layer, "deterministic": True, "why": spec["why"],
                "picks": [], "note": "no model needed — deterministic stage"}
    from routing import recommend
    r = recommend(task=task, limit=limit)
    picks = [{"model": p["model"], "provider": p["provider"], "free": p["free"],
              "q": p["q"], "benchmark": p.get("benchmark"), "cost": p["cost"],
              "task_fit": task, "value": (p["q"] / p["cost"]) if p["cost"] > 0 else float("inf")}
             for p in r["picks"]]
    return {"layer": layer, "task": task, "prefer_free": spec["prefer_free"],
            "why": spec["why"], "picks": picks}


def _db_models() -> dict:
    db = json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8"))
    return db.get("models", {})


def layer_config() -> dict:
    """A worker-consumable config: layer → {model, why, task} — for setting HERMES_MODEL per layer."""
    cfg = {}
    for layer in LAYER_MAP:
        r = recommend_layer(layer, limit=1)
        if r.get("deterministic"):
            cfg[layer] = {"model": "NONE", "deterministic": True, "why": r["why"]}
        elif r.get("picks"):
            top = r["picks"][0]
            cfg[layer] = {"model": top["model"], "task": r["task"], "why": r["why"],
                          "cost_per_task": top["cost"], "free": top["free"]}
    return cfg


def render(cfg: dict) -> str:
    lines = ["# deal-radar per-layer model config (for the translation workers — set HERMES_MODEL)"]
    for layer, c in cfg.items():
        if c.get("deterministic"):
            lines.append(f"{layer:<8} NO-MODEL (deterministic)")
        else:
            lines.append(f"{layer:<8} {c['model']:<40} task={c['task']:<10} free={c.get('free')}  # {c['why']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys as _s
    if len(_s.argv) > 1 and _s.argv[1] == "--config":
        print(render(layer_config()))
    else:
        for layer in ["T1", "ARGMAP", "L2", "L200", "C1"]:
            r = recommend_layer(layer, limit=1)
            if r.get("picks"):
                p = r["picks"][0]
                print(f"{layer:<8} {p['model'][:44]:<46} task={r['task']:<10} free={p['free']}  # {r['why'][:40]}")
