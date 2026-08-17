#!/usr/bin/env python3
"""app/test_compute_sources.py — proof for the free-pool compute-source registry."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import compute_sources as CS

GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    print("COMPUTE-SOURCES — proof (free-pool classes, router tiers)\n")

    fp = CS.free_pool()
    gate("free pool has the classes", len(fp["order"]) >= 7, f"{len(fp['order'])} sources")
    gate("webllm is T0 (free-first)", fp["order"][0] == "webllm", fp["order"][0])
    gate("petals reachable from box", "petals" in fp["reachable_from_box"], str(fp["reachable_from_box"]))
    gate("webllm not reachable from server", "webllm" not in fp["reachable_from_box"],
         "browser-side, correct to exclude")

    tiers = CS.as_router_tiers()
    gate("tiers are ordered", tiers[0]["tier"] == 0 and tiers[-1]["tier"] == len(tiers) - 1)
    gate("all tiers are free", all(t["cost_per_token"] == 0.0 for t in tiers), "free pool = \$0")
    gate("petals tier present + reachable", any(t["name"] == "petals" and t["reachable_from_box"] for t in tiers))

    # the router ladder concept: free-pool before paid API tiers
    pool_names = [t["name"] for t in tiers]
    gate("free pool names ordered", pool_names == sorted(pool_names, key=lambda n: CS.COMPUTE_SOURCES[n]["order"]),
         str(pool_names))

    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
# OLD_TEST: Use invariant_tests.py instead
