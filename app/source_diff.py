"""app/source_diff.py — Semantic diff for offer snapshots.

Compares previous vs current state of offers, keyed by model_id.
Detects price changes, free tier transitions, quota changes, etc.
"""
from __future__ import annotations

from typing import Any


def diff_snapshots(prev: dict, curr: dict) -> list[dict]:
    """Compare previous vs current offer states.
    
    Both prev and curr must be dicts keyed by model_id.
    Returns list of change events.
    """
    if not isinstance(prev, dict) or not isinstance(curr, dict):
        return []

    changes = []

    # Detect offers in current that weren't in previous (new offers)
    for model_id, curr_state in curr.items():
        if model_id not in prev:
            changes.append({
                "field": "offer_added",
                "model_id": model_id,
                "event_type": "offer_added",
                "current": curr_state,
            })
            continue

        prev_state = prev[model_id]
        # Compare fields
        field_changes = _compare_fields(prev_state, curr_state, model_id)
        changes.extend(field_changes)

    # Detect offers in previous that aren't in current (removed offers)
    for model_id in prev:
        if model_id not in curr:
            changes.append({
                "field": "offer_removed",
                "model_id": model_id,
                "event_type": "offer_removed",
                "previous": prev[model_id],
            })

    return changes


def _compare_fields(prev: dict, curr: dict, model_id: str) -> list[dict]:
    """Compare two offer states field by field."""
    changes = []
    
    # Fields to compare with their transition types
    fields = {
        "free": _classify_free_transition,
        "input_per_m": lambda p, c: _classify_price_transition(p, c, "input_per_m"),
        "output_per_m": lambda p, c: _classify_price_transition(p, c, "output_per_m"),
        "context_tokens": lambda p, c: _classify_value_change(p, c, "context_tokens"),
        "requests_day": lambda p, c: _classify_value_change(p, c, "requests_day"),
    }
    
    for field_name, classifier in fields.items():
        prev_val = prev.get(field_name)
        curr_val = curr.get(field_name)
        if prev_val != curr_val:
            change = classifier(prev_val, curr_val)
            if change:
                change["model_id"] = model_id
                changes.append(change)
    
    return changes


def _classify_free_transition(prev: Any, curr: Any) -> dict | None:
    """Classify free tier transition."""
    if prev is None and curr is None:
        return None
    if prev == curr:
        return None
    
    # false → true = free_started (model became free)
    # true → false = free_ended (model stopped being free)
    if not prev and curr:
        return {"field": "free", "event_type": "free_started", "previous": prev, "current": curr}
    elif prev and not curr:
        return {"field": "free", "event_type": "free_ended", "previous": prev, "current": curr}
    else:
        return {"field": "free", "event_type": "free_changed", "previous": prev, "current": curr}


def _classify_price_transition(prev: Any, curr: Any, field: str) -> dict | None:
    """Classify price change."""
    if prev is None and curr is None:
        return None
    if prev == curr:
        return None
    
    if prev is None and curr is not None:
        return {"field": field, "event_type": "price_discovered", "previous": prev, "current": curr}
    elif prev is not None and curr is None:
        return {"field": field, "event_type": "price_lost", "previous": prev, "current": curr}
    elif prev is not None and curr is not None:
        if curr < prev:
            return {"field": field, "event_type": "price_drop", "previous": prev, "current": curr}
        elif curr > prev:
            return {"field": field, "event_type": "price_increase", "previous": prev, "current": curr}
    return None


def _classify_value_change(prev: Any, curr: Any, field: str) -> dict | None:
    """Classify general value change."""
    if prev == curr:
        return None
    return {"field": field, "event_type": "value_changed", "previous": prev, "current": curr}
