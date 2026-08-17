"""app/history.py — Historical snapshot comparison.

Tracks changes over time by comparing current vs previous snapshots.
Records: what changed, when, and the delta.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / "data" / "history"
CHANGE_LOG = ROOT / "data" / "change-log.jsonl"


def save_snapshot_snapshot(snapshot_name: str, offers: list[dict]):
    """Save a snapshot for historical comparison."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    snapshot = {
        "timestamp": ts,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "name": snapshot_name,
        "offer_count": len(offers),
        "offers": {o.get("model_id", ""): {
            "provider": o.get("provider_id"),
            "input_per_m": o.get("input_per_m"),
            "output_per_m": o.get("output_per_m"),
            "free": o.get("free"),
            "requests_per_5h": o.get("metadata", {}).get("requests_per_5h"),
            "multiplier": o.get("metadata", {}).get("multiplier"),
            "capacity_multiplier": o.get("metadata", {}).get("capacity_multiplier"),
            "context_tokens": o.get("context_tokens"),
        } for o in offers if o.get("model_id")},
    }
    path = HISTORY_DIR / ("%s_%d.json" % (snapshot_name, ts))
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    return path


def compare_snapshots(prev_path: str, curr_path: str) -> dict:
    """Compare two snapshots and return changes."""
    prev = json.loads(Path(prev_path).read_text())
    curr = json.loads(Path(curr_path).read_text())

    changes = []
    prev_offers = prev.get("offers", {})
    curr_offers = curr.get("offers", {})

    # New offers
    for model_id in curr_offers:
        if model_id not in prev_offers:
            changes.append({
                "type": "new_offer",
                "model_id": model_id,
                "details": curr_offers[model_id],
            })

    # Removed offers
    for model_id in prev_offers:
        if model_id not in curr_offers:
            changes.append({
                "type": "removed_offer",
                "model_id": model_id,
                "details": prev_offers[model_id],
            })

    # Changed offers
    for model_id in curr_offers:
        if model_id in prev_offers:
            curr_o = curr_offers[model_id]
            prev_o = prev_offers[model_id]
            field_changes = []
            for field in ["input_per_m", "output_per_m", "free", "requests_per_5h",
                          "multiplier", "capacity_multiplier", "context_tokens"]:
                cv = curr_o.get(field)
                pv = prev_o.get(field)
                if cv != pv:
                    field_changes.append({
                        "field": field,
                        "previous": pv,
                        "current": cv,
                    })
            if field_changes:
                changes.append({
                    "type": "changed_offer",
                    "model_id": model_id,
                    "changes": field_changes,
                })

    return {
        "prev_snapshot": prev.get("name"),
        "curr_snapshot": curr.get("name"),
        "prev_timestamp": prev.get("timestamp_iso"),
        "curr_timestamp": curr.get("timestamp_iso"),
        "total_changes": len(changes),
        "new_offers": sum(1 for c in changes if c["type"] == "new_offer"),
        "removed_offers": sum(1 for c in changes if c["type"] == "removed_offer"),
        "changed_offers": sum(1 for c in changes if c["type"] == "changed_offer"),
        "changes": changes,
    }


def get_latest_comparison() -> dict | None:
    """Compare the two most recent snapshots."""
    if not HISTORY_DIR.exists():
        return None
    files = sorted(HISTORY_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
    if len(files) < 2:
        return None
    return compare_snapshots(str(files[-2]), str(files[-1]))
