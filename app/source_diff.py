"""Semantic diff engine for comparing offer snapshots."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

CHANGE_DETECTORS = {
    "price_usd": "price_change",
    "discount_percent": "discount_change",
    "free_tier": "free_tier_change",
    "rate_limit_rpm": "rate_limit_change",
    "rate_limit_rpd": "rate_limit_change",
    "rate_limit_tpd": "rate_limit_change",
    "multiplier": "multiplier_change",
    "quota_tokens": "quota_change",
    "quota_requests": "quota_change",
    "context_window": "context_change",
    "promo_expiry": "expiry_change",
}


def _classify_change(key: str, prev_val: Any, curr_val: Any) -> dict:
    """Classify the nature of a single field change."""
    event_type = CHANGE_DETECTORS.get(key, "field_change")

    direction = "increased"
    if prev_val is None and curr_val is not None:
        direction = "added"
    elif prev_val is not None and curr_val is None:
        direction = "removed"
    elif prev_val is not None and curr_val is not None:
        try:
            if isinstance(prev_val, (int, float)) and isinstance(curr_val, (int, float)):
                direction = "increased" if curr_val > prev_val else "decreased"
            elif str(prev_val) != str(curr_val):
                direction = "modified"
        except Exception:
            direction = "modified"

    if event_type == "price_change" and direction == "decreased":
        event_type = "price_drop"
    elif event_type == "price_change" and direction == "increased":
        event_type = "price_increase"

    if key == "free_tier":
        if prev_val and not curr_val:
            event_type = "free_started"
        elif not prev_val and curr_val:
            event_type = "free_ended"
        elif prev_val and curr_val:
            event_type = "free_modified"

    return {
        "event_type": event_type,
        "field": key,
        "direction": direction,
        "previous_value": prev_val,
        "current_value": curr_val,
    }


def diff_snapshots(prev: dict, curr: dict) -> list[dict]:
    """Compare two snapshots of the same offer and detect changes.

    Args:
        prev: Previous snapshot of the offer.
        curr: Current snapshot of the offer.

    Returns:
        List of change event dicts with fields:
            event_type, field, direction, previous_value, current_value
    """
    if not isinstance(prev, dict) or not isinstance(curr, dict):
        logger.error("Both prev and curr must be dicts, got %s and %s", type(prev), type(curr))
        return []

    changes: list[dict] = []
    all_keys = set(list(prev.keys()) + list(curr.keys()))

    for key in sorted(all_keys):
        prev_val = prev.get(key)
        curr_val = curr.get(key)

        if prev_val == curr_val:
            continue

        try:
            change = _classify_change(key, prev_val, curr_val)
            changes.append(change)
            logger.debug("Change detected in field '%s': %s", key, change["event_type"])
        except Exception as exc:
            logger.error("Failed to classify change for field '%s': %s", key, exc)

    if changes:
        logger.info("Detected %d changes between snapshots", len(changes))
    else:
        logger.debug("No changes detected between snapshots")

    return changes
