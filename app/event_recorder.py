"""Record deal events from source_diff and promo_extract.

One append-only event log. No parallel systems.
Events are wired to OFFERS, not sources.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import canonical_db


def record_event(conn, offer_id: str, event_type: str,
                 previous_value: dict = None, current_value: dict = None,
                 source_url: str = "", confidence: float = 0.8):
    """Record a deal event.
    
    Args:
        offer_id: Canonical offer_id (NOT source_id)
        event_type: Type of event (price_change, new_deal, expired, etc.)
        previous_value: Previous state (for changes)
        current_value: Current state (for changes)
        source_url: Source of the event
        confidence: Confidence level
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO deal_events (offer_id, event_type, previous_value, current_value, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (offer_id, event_type,
          json.dumps(previous_value) if previous_value else None,
          json.dumps(current_value) if current_value else None, now))


def record_changes(conn, offer_id: str, changes: list[dict], source_url: str = ""):
    """Record changes from source_diff.
    
    Args:
        offer_id: Canonical offer_id (NOT source_id)
        changes: List of changes detected
        source_url: Source URL
    """
    for change in changes:
        event_type = change.get("event_type", "unknown")
        record_event(conn, offer_id, event_type,
                     previous_value=change.get("previous"),
                     current_value=change.get("current"),
                     source_url=source_url)


def record_new_deal(conn, offer_id: str, source_url: str = ""):
    """Record a new deal discovery."""
    record_event(conn, offer_id, "new_deal",
                 current_value={"discovered": True},
                 source_url=source_url)


def record_price_change(conn, offer_id: str, old_price: dict, new_price: dict,
                        source_url: str = ""):
    """Record a price change."""
    record_event(conn, offer_id, "price_change",
                 previous_value=old_price,
                 current_value=new_price,
                 source_url=source_url)


def record_deal_expiry(conn, offer_id: str, source_url: str = ""):
    """Record a deal expiry."""
    record_event(conn, offer_id, "deal_expired",
                 previous_value={"status": "active"},
                 current_value={"status": "expired"},
                 source_url=source_url)
