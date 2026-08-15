#!/usr/bin/env python3
"""app/test_layer_recommend.py — proof for the per-layer model recommendation."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import layer_recommend as LR

GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    print("LAYER-RECOMMEND — proof (per-layer model for the translation stack)\n")

    # every model layer maps to a task + returns a pick
    for layer, task in [("T1", "extraction"), ("ARGMAP", "reasoning"),
                        ("L2", "research"), ("L200", "reasoning"), ("C1", "research")]:
        r = LR.recommend_layer(layer, limit=1)
        gate(f"{layer} maps to {task} + picks", r.get("task") == task and len(r.get("picks", [])) > 0,
             r["picks"][0]["model"] if r.get("picks") else "none")

    # deterministic layers → no model
    l0 = LR.recommend_layer("L0")
    gate("L0 deterministic", l0.get("deterministic") is True, l0.get("why"))

    # the config is worker-consumable (HERMES_MODEL per layer)
    cfg = LR.layer_config()
    gate("config has all layers", set(["T1", "ARGMAP", "L2", "L200", "C1", "L0", "L1"]) <= set(cfg),
         str(list(cfg)))
    gate("model layers have a model", cfg["T1"].get("model") and cfg["L2"].get("model"),
         f"T1={cfg['T1']['model'][:20]} L2={cfg['L2']['model'][:20]}")
    gate("deterministic layers are NONE", cfg["L0"]["model"] == "NONE", cfg["L0"]["model"])

    # different layers give different models (the point: each layer its own model)
    models = {lr: cfg[lr]["model"] for lr in ["T1", "ARGMAP", "L2", "L200", "C1"]}
    gate("layers differentiate models", len(set(models.values())) >= 2,
         str(set(models.values())))

    # unknown layer rejected
    bad = LR.recommend_layer("ZZZ")
    gate("unknown layer rejected", "error" in bad, bad.get("error", "")[:40])

    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
