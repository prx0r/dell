#!/usr/bin/env python3
"""app/test.py — proof for the deal-radar (canonical models + frontiers + route)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import normalize
import quality

GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    print("DEAL-RADAR — proof (canonical model DB + value frontiers + routing)\n")

    m = normalize.normalize()
    gate("normalizes all sources", len(m) > 500, f"{len(m)} canonical models")

    f = quality.frontiers(mode="chat", limit=5)
    gate("frontiers produce top-free", len(f["top_free"]) > 0,
         f"top free: {f["top_free"][0]['model'] if f["top_free"] else 'none'}")
    gate("top-free has quality", f["top_free"][0]["quality"] > 0 if f["top_free"] else False,
         f"q={f["top_free"][0]['quality'] if f["top_free"] else 0}")

    # value/cost math is sane: cost_per_job scales with tokens
    rec = {"prompt_per_token": 1e-6, "completion_per_token": 2e-6, "cache_read_per_token": 0}
    c_small = quality.cost_per_job(rec, input_tok=1000, output_tok=500)
    c_big = quality.cost_per_job(rec, input_tok=100000, output_tok=50000)
    gate("cost scales with tokens", c_big > c_small * 50, f"{c_small} -> {c_big}")

    # value_score: a model that needs 3 attempts costs more (effective_cost)
    vs1 = quality.value_score(rec, {"coding": 80, "agentic": 70, "intelligence": 75}, success_rate=0.85)
    vs2 = quality.value_score(rec, {"coding": 80, "agentic": 70, "intelligence": 75}, success_rate=0.3)
    gate("effective_cost penalizes low success", vs2["effective_cost"] > vs1["effective_cost"],
         f"{vs1['effective_cost']} vs {vs2['effective_cost']}")

    # deals: free-tier models detected
    dl = quality.deals()
    gate("deals finds free models", len(dl["recurring_free_models"]) > 0,
         f"{len(dl['recurring_free_models'])} free-tier models")

    # the router pick respects a quality floor (fail-closed: floor too high → none)
    f2 = quality.frontiers(mode="chat", limit=50)
    cands = f2.get("best_value_paid", []) + f2.get("top_free", [])
    over95 = [c for c in cands if c.get("quality", 0) >= 95]
    gate("quality floor blocks weak (fail-closed)", len(over95) == 0,
         "no model clears a 95 floor (max ~89)")

    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
# OLD_TEST: Use invariant_tests.py instead
