"""Record deal events from source_diff and promo_extract.

One append-only event log. No parallel systems.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import canonical_db


def record_event(conn, deal_id: str, event_type: str,
                 previous_value: dict = None, current_value: dict = None,
                 source_url: str = "", confidence: float = 0.8):
    """Record a deal event."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO deal_events (deal_id, event_type, effective_at, observed_at,
            previous_json, current_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (deal_id, event_type, now, now,
          json.dumps(previous_value) if previous_value else None,
          json.dumps(current_value) if current_value else None))


def record_changes(conn, offer_id: str, changes: list[dict], source_url: str = ""):
    """Record changes from source_diff."""
    for change in changes:
        event_type = change.get("event_type", "unknown")
        record_event(conn, offer_id, event_type,
                     previous_value=change.get("previous"),
                     current_value=change.get("current"),
                     source_url=source_url)
