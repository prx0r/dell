#!/usr/bin/env python3
"""app/test_task_ranking.py — proof for the task-aware sorting + rate limits + validation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import task_ranking as TR
import rate_limits as RL
import compute_sources as CS

GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    print("TASK-RANKING + RATE-LIMITS — proof\n")

    # task profiles exist
    gate("task profiles defined", len(TR.TASKS) >= 5, str(TR.TASKS))
    gate("coding is the default task", TR.DEFAULT_TASK == "coding")

    # a fake model: ranking returns it with a score
    db = json.loads((ROOT / "data" / "canonical-models.json").read_text(encoding="utf-8"))
    models = db.get("models", {})
    r = TR.rank(models, {}, task="coding", limit=5)
    gate("coding ranking produces models", len(r) > 0, f"{len(r)} models")
    if r:
        gate("ranking is sorted desc", all(r[i]["score"] >= r[i + 1]["score"] for i in range(len(r) - 1)),
             f"top score {r[0]['score']}")
        gate("ranking has per-axis data", "task_quality" in r[0] and "cost_per_task" in r[0],
             f"q={r[0]['task_quality']} cost={r[0]['cost_per_task']}")

    # long-context enforces min 128k
    rl = TR.rank(models, {}, task="long-context", limit=5)
    gate("long-context returns eligible", len(rl) > 0, f"{len(rl)} models")
    if rl:
        gate("long-context models have big ctx", all((m["context"] or 0) >= 128000 for m in rl),
             f"min ctx {min(m['context'] for m in rl)}")

    # rate limits
    rlr = RL.all_rate_limits()
    gate("rate-limits has free providers", "groq" in rlr["providers"] and "cloudflare" in rlr["providers"])
    gate("groq quota present", RL.provider_quota("groq").get("rpd") is not None,
         str(RL.provider_quota("groq").get("rpd")))

    # compute sources
    cs = CS.free_pool()
    gate("compute sources exist", len(cs["order"]) >= 7, str(cs["order"][:3]))

    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
# OLD_TEST: Use invariant_tests.py instead
