#!/usr/bin/env python3
"""app/test_advanced_query.py — proof for the natural-language usage-profile router."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import advanced_query as AQ

GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    print("ADVANCED-QUERY — proof (usage-profile aware routing)\n")

    # batch image → extraction task + image modality + batch strategy
    p = AQ.parse("I need an image model for batch work")
    gate("batch parses task+modality", p["task"] == "extraction" and p["modality"] == "image" and p["batch"],
         f"{p['task']}/{p['modality']}/batch={p['batch']}")

    # 4 calls/day → interactive (low volume), daily parsed
    p2 = AQ.parse("I need an image model for 4 calls per day")
    gate("daily-calls parsed", p2["daily_calls"] == 4, f"daily={p2['daily_calls']}")
    gate("4/day is interactive", p2["batch"] is False, f"batch={p2['batch']}")

    # batch strategy uses cheap :batch models
    r = AQ.recommend_for_query("image model for batch work", limit=10)
    gate("batch picks exist", len(r["picks"]) > 0, f"{len(r['picks'])}")
    gate("batch strategy set", "batch" in r["volume_strategy"].lower(), r["volume_strategy"])

    # interactive strategy → quality first; the PAID picks differ (free-first model is shared)
    r2 = AQ.recommend_for_query("image model for 4 calls per day", limit=10)
    gate("interactive strategy set", "interactive" in r2["volume_strategy"].lower(), r2["volume_strategy"])
    paid1 = [p for p in r["picks"] if not p["free"]]
    paid2 = [p for p in r2["picks"] if not p["free"]]
    gate("paid picks differ by volume", paid1 and paid2 and paid1[0]["model"] != paid2[0]["model"],
         f"{paid1[0]['model'] if paid1 else 'none'} vs {paid2[0]['model'] if paid2 else 'none'}")

    # reasoning query maps to reasoning task
    p3 = AQ.parse("I need a model for hard reasoning problems")
    gate("reasoning task detected", p3["task"] == "reasoning", p3["task"])

    # rate-limit annotation present
    gate("picks carry rate-limit fields", "rpm" in r["picks"][0] and "fits_daily_volume" in r["picks"][0],
         f"rpm={r['picks'][0]['rpm']}")

    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
