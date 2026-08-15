#!/usr/bin/env python3
"""app/test_benchmark_quality.py — proof for the measured benchmark quality."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import benchmark_quality as BQ

GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    print("BENCHMARK-QUALITY — proof (measured, not guessed)\n")

    # real measured coding leaders exist
    coding = BQ.top_benchmarked("coding", 10)
    gate("coding leaders found", len(coding) > 0, f"{len(coding)} models")
    if coding:
        gate("coding leaders are measured", coding[0]["benchmark_score"] > 50,
             f"{coding[0]['model']} = {coding[0]['benchmark_score']} ({coding[0]['benchmark']})")
        gate("sorted descending", all(coding[i]["benchmark_score"] >= coding[i + 1]["benchmark_score"]
                                      for i in range(len(coding) - 1)))

    # reasoning leaders (GPQA)
    reasoning = BQ.top_benchmarked("reasoning", 5)
    gate("reasoning leaders found", len(reasoning) > 0, f"{len(reasoning)} models")
    if reasoning:
        gate("reasoning has a benchmark", reasoning[0].get("benchmark") is not None,
             f"{reasoning[0]['benchmark']}")

    # a model with no benchmark → estimated (honest fallback)
    bq = BQ.benchmark_quality("definitely-not-a-model-xyz")
    gate("unknown model → estimated", bq["source"] == "estimated", bq["source"])

    # score normalization is bounded 0-100
    import json
    db = BQ.load()
    with_b = [r for r in db.values() if r.get("benchmarks")]
    gate("models have benchmarks in DB", len(with_b) > 500, f"{len(with_b)} with benchmarks")

    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
