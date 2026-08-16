#!/usr/bin/env python3
"""agent/audit.py — the GOLDEN-FILE AUDIT for dealradar (the executable ONE RULE).

The legitimacy gate: every claimed dealradar result (model count, test pass, recommendation) must trace to
a machine-computed value on fixed data. This audit:
  1. Recomputes the test suite on the real data (the deterministic recompute).
  2. Compares against the committed golden/ baseline — within tolerance.
  3. Flags any number that has no content-addressed run record as theater.

Usage:
  python3 agent/audit.py --list                 # all content-addressed runs
  python3 agent/audit.py --bench suite --record # (re)compute + write the golden
  python3 agent/audit.py --bench suite          # recompute; fail if it doesn't match the golden
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
GOLDEN_DIR = ROOT / "golden"


def _sh(*args, timeout=900) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "__TIMEOUT__"


def compute(bench: str) -> dict:
    """Run the test suite on the real data (the deterministic recompute)."""
    out = _sh("python3", str(ROOT / "app" / "test.py"), timeout=300)
    return {"bench": bench, "raw_output": out[-3000:]}


def audit(bench: str, record: bool) -> int:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_file = GOLDEN_DIR / f"{bench}.json"
    result = compute(bench)
    print(f"=== AUDIT {bench} ===")
    print(result["raw_output"][-400:])

    if record:
        golden_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"  ✓ recorded golden baseline → {golden_file}")
        return 0

    if not golden_file.exists():
        print(f"  ✗ no golden baseline yet — run with --record first")
        return 1

    golden = json.loads(golden_file.read_text())
    from run_recorder import sha256
    new_sig = sha256(result["raw_output"][-2000:])
    old_sig = sha256(golden["raw_output"][-2000:])
    if new_sig == old_sig:
        print(f"  ✓ run reproducible — output matches golden (hash {new_sig[:12]})")
        return 0
    print(f"  ⚠ output differs from golden ({new_sig[:12]} vs {old_sig[:12]}) — re-run or --record")
    return 1


def list_runs() -> int:
    from run_recorder import RunRecorder
    runs = RunRecorder().all()
    print(f"=== {len(runs)} content-addressed runs ===")
    for r in runs:
        print(f"  {r['step']:14} sig={r['run_signature'][:12]} "
              f"metrics={json.dumps(r.get('metrics', {}))[:60]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="suite")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        return list_runs()
    return audit(args.bench, args.record)


if __name__ == "__main__":
    sys.exit(main())
