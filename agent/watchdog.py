#!/usr/bin/env python3
"""agent/watchdog.py — the autonomous dealradar watchdog (hermes cron).

Runs a bounded health + freshness cycle on a schedule:
  1. refresh (check live prices + drift)
  2. canary (probe the free providers, live)
  3. validate (run the test suite — the gate)
  4. report the canonical model count + health

Honesty + box rules: refresh/canary hit the network — run one at a time, log everything, never fabricate.
Safe to run via hermes cron daily.

Usage:
  python3 agent/watchdog.py            # full cycle
  python3 agent/watchdog.py --dry-run  # show what it would do
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _sh(*args, timeout=900) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "__TIMEOUT__"


def _log(record: dict) -> None:
    reg = ROOT / "data" / "watchdog.jsonl"
    reg.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with open(reg, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def cycle(dry_run: bool) -> None:
    print(f"=== WATCHDOG {datetime.now(timezone.utc).isoformat()} (dry={dry_run}) ===")
    results = {}
    steps = {
        "report": [str(ROOT / "agent" / "run.py"), "--step", "report"],
        "canary": [str(ROOT / "agent" / "run.py"), "--step", "canary"],
        "validate": [str(ROOT / "agent" / "run.py"), "--step", "validate"],
    }
    for name, cmd in steps.items():
        if dry_run:
            print(f"  [dry] would run: {' '.join(cmd[-3:])}")
            results[name] = "dry"
            continue
        out = _sh("python3", *cmd, timeout=900)
        results[name] = out[-1200:]
        print(out[-400:])
    _log({"dry_run": dry_run, "results": {k: v[:200] for k, v in results.items()}})
    print(f"\n=== WATCHDOG CYCLE DONE (logged) ===")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cycle(args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
