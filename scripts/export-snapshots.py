#!/usr/bin/env python3
"""scripts/export-snapshots.py — Export SQLite canonical DB to snapshots/ for Astro build + MCP.

Reads from data/llmdeals.sqlite3, writes to snapshots/*.json (one file per source).
Also exports a combined all-offers.json for the site.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "llmdeals.sqlite3"
SNAPSHOTS_DIR = ROOT / "snapshots"


def export():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run: python3 -m app.cron_poll  (to populate the DB first)")
        sys.exit(1)

    SNAPSHOTS_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get all offers from the canonical table
    try:
        rows = conn.execute("""
            SELECT * FROM offers ORDER BY provider_id, model_id
        """).fetchall()
    except sqlite3.OperationalError as e:
        print(f"ERROR: Could not read offers table: {e}")
        print("Tables:", [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
        sys.exit(1)

    if not rows:
        print("WARNING: No offers found in database")
        return

    # Group by source/provider
    by_source = {}
    for row in rows:
        d = dict(row)
        source = d.get("source_id") or d.get("provider_id") or "unknown"
        by_source.setdefault(source, []).append(d)

    # Write per-source snapshots
    total = 0
    for source, offers in by_source.items():
        safe_name = source.replace("/", "_").replace(" ", "_").lower()
        path = SNAPSHOTS_DIR / f"{safe_name}.json"
        with open(path, "w") as f:
            json.dump({"source": source, "count": len(offers), "offers": offers}, f, indent=2, default=str)
        total += len(offers)
        print(f"  {safe_name}.json: {len(offers)} offers")

    # Write combined all-offers.json
    all_path = SNAPSHOTS_DIR / "all-offers.json"
    with open(all_path, "w") as f:
        json.dump({"count": len(rows), "offers": [dict(r) for r in rows]}, f, indent=2, default=str)

    # Write events snapshot if events table exists
    try:
        events = conn.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT 200").fetchall()
        events_path = SNAPSHOTS_DIR / "events.json"
        with open(events_path, "w") as f:
            json.dump([dict(e) for e in events], f, indent=2, default=str)
        print(f"  events.json: {len(events)} events")
    except sqlite3.OperationalError:
        pass

    conn.close()
    print(f"\nExported {total} offers to {SNAPSHOTS_DIR}/")


if __name__ == "__main__":
    export()
