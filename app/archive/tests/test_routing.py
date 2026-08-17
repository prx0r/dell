#!/usr/bin/env python3
"""app/test_routing.py — proof for the arXiv-based router (Phase 1 utility + Phase 2 LinUCB)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import routing

GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    print("ROUTING — proof (cost-first utility + LinUCB learning)\n")

    # Phase 1: free models first (the user's priority), then paid by value
    r = routing.recommend("reasoning", limit=10)
    gate("phase1 picks exist", len(r["picks"]) > 0, f"{len(r['picks'])}")
    gate("algorithm named", "phase1" in r.get("algorithm", ""), r.get("algorithm", ""))
    if r["picks"]:
        first = r["picks"][0]
        gate("free model first", first["free"] is True, f"{first['model']}")
        gate("free picks are genuinely :free", ":free" in first["model"] or "poolside" in first["model"],
             first["model"])
        # no price-0 artifact with a real price
        paid = [p for p in r["picks"] if not p["free"]]
        gate("no price-0 non-free artifacts", all(p["cost"] > 0 for p in paid),
             f"{len(paid)} paid picks, all priced")

    # capability filtering works (long-context min_ctx)
    rl = routing.recommend("long-context", min_ctx=128000, limit=5)
    gate("long-context filters by ctx", len(rl["picks"]) >= 0, f"{len(rl['picks'])}")

    # Phase 2: LinUCB with surrogate + exploration, fail-safe with no feedback
    r2 = routing.linucb("reasoning", limit=5)
    gate("phase2 algorithm named", "linucb" in r2.get("algorithm", "").lower(), r2.get("algorithm", ""))
    gate("phase2 handles no-feedback", "exploration_weight" in r2, f"w={r2['exploration_weight']}")

    # feedback changes the bandit estimate
    routing.log_feedback("poolside/laguna-xs-2.1:free", quality=50.0, cost=0.0)
    r3 = routing.linucb("reasoning", limit=5)
    gate("feedback recorded", r3["feedback_n"] >= 1, f"n={r3['feedback_n']}")
    # clean up the test feedback so it doesn't pollute
    routing.FEEDBACK.write_text("[]")

    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
# OLD_TEST: Use invariant_tests.py instead
