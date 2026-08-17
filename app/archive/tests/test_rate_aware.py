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
    print("RATE-AWARE — proof (free is best ONLY if it can serve the workload)\n")
    # a big batch job penalizes rate-limited free models
    big = routing.recommend('extraction', daily_calls=5000, volume_importance=0.5, limit=5)
    gate("big batch → free penalized", any(p.get('quota_penalty', 0) > 0 for p in big['picks']),
         f"max penalty {max(p.get('quota_penalty',0) for p in big['picks'])}")
    free_big = [p for p in big['picks'] if p['free']]
    gate("free models capped rpd=50", free_big and free_big[0].get('rpd') == 50,
         f"rpd={free_big[0].get('rpd') if free_big else 'none'}")
    # a tiny job → free is fine (no penalty)
    small = routing.recommend('extraction', daily_calls=4, volume_importance=0.5, limit=3)
    gate("small batch → no penalty", all(p.get('quota_penalty', 0) == 0 for p in small['picks']),
         f"penalties {[p.get('quota_penalty') for p in small['picks']]}")
    # free wins for small volume
    gate("free wins for small", small['picks'][0]['free'] is True, small['picks'][0]['model'])
    passed = sum(1 for _, ok in GATES if ok)
    print(f"\n=== SUMMARY: {passed}/{len(GATES)} PASS ===\n")
    return 0 if passed == len(GATES) else 1

if __name__ == "__main__":
    sys.exit(main())
# OLD_TEST: Use invariant_tests.py instead
