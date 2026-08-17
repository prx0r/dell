"""app/expiry.py — Precise deal expiry tracking.

Tracks promotions with hour-level precision, not just dates.
Detects: active, expiring_soon, expired, ended, unknown.

Key insight: "3 days left" is useful. "Ends Dec 31" is not.
We track:
- expires_at (ISO timestamp when known)
- hours_remaining (computed from now)
- status (active | expiring_soon | expired | ended | unknown)
- last_verified (when we last confirmed this deal is real)
- verification_source (which source confirmed it)
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_expiry(text: str) -> dict | None:
    """Extract expiry information from text. Returns None if no expiry found.

    Handles formats like:
    - "ends December 31, 2026"
    - "promo ends in 3 days"
    - "limited time offer"
    - "expires 2026-12-31"
    - "through Jan 15"
    - "until midnight UTC"
    - "ends today"
    - "48 hours left"
    """
    text_lower = text.lower()
    now = datetime.now(timezone.utc)

    # Absolute date patterns
    date_patterns = [
        # "ends December 31, 2026"
        (r'ends?\s+(\w+\s+\d{1,2},?\s+\d{4})', lambda m: _parse_absolute_date(m.group(1))),
        # "expires 2026-12-31"
        (r'expir(?:es?|y|ation)\s+(\d{4}-\d{2}-\d{2})', lambda m: _parse_iso_date(m.group(1))),
        # "through Jan 15, 2026"
        (r'through\s+(\w+\s+\d{1,2},?\s+\d{4})', lambda m: _parse_absolute_date(m.group(1))),
        # "through 2026-01-15"
        (r'through\s+(\d{4}-\d{2}-\d{2})', lambda m: _parse_iso_date(m.group(1))),
        # "until 2026-12-31"
        (r'until\s+(\d{4}-\d{2}-\d{2})', lambda m: _parse_iso_date(m.group(1))),
    ]

    for pattern, parser in date_patterns:
        match = re.search(pattern, text_lower)
        if match:
            dt = parser(match)
            if dt:
                hours = (dt - now).total_seconds() / 3600
                return {
                    "expires_at": dt.isoformat(),
                    "hours_remaining": round(hours, 1),
                    "status": _status_from_hours(hours),
                    "precision": "date",
                    "raw": match.group(0),
                }

    # Relative patterns
    relative_patterns = [
        # "ends in 3 days"
        (r'ends?\s+in\s+(\d+)\s+days?', lambda m: timedelta(days=int(m.group(1)))),
        # "ends in 48 hours"
        (r'ends?\s+in\s+(\d+)\s+hours?', lambda m: timedelta(hours=int(m.group(1)))),
        # "3 days left"
        (r'(\d+)\s+days?\s+left', lambda m: timedelta(days=int(m.group(1)))),
        # "48 hours left"
        (r'(\d+)\s+hours?\s+left', lambda m: timedelta(hours=int(m.group(1)))),
        # "ends today"
        (r'ends?\s+today', lambda m: timedelta(hours=23, minutes=59)),
        # "ends tomorrow"
        (r'ends?\s+tomorrow', lambda m: timedelta(days=1, hours=23, minutes=59)),
    ]

    for pattern, delta_fn in relative_patterns:
        match = re.search(pattern, text_lower)
        if match:
            delta = delta_fn(match)
            dt = now + delta
            hours = delta.total_seconds() / 3600
            return {
                "expires_at": dt.isoformat(),
                "hours_remaining": round(hours, 1),
                "status": _status_from_hours(hours),
                "precision": "relative",
                "raw": match.group(0),
            }

    # Vague signals (no precise date)
    vague_signals = [
        "limited time", "for a limited time", "while supplies last",
        "launch pricing", "introductory", "promotional",
    ]
    for signal in vague_signals:
        if signal in text_lower:
            return {
                "expires_at": None,
                "hours_remaining": None,
                "status": "active",
                "precision": "vague",
                "raw": signal,
                "note": "No expiry date — could end anytime",
            }

    return None


def _parse_absolute_date(text: str) -> datetime | None:
    """Parse 'December 31, 2026' style dates."""
    for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"]:
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_iso_date(text: str) -> datetime | None:
    """Parse '2026-12-31' style dates."""
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _status_from_hours(hours: float) -> str:
    if hours < 0:
        return "expired"
    elif hours < 4:
        return "expiring_imminent"
    elif hours < 24:
        return "expiring_soon"
    elif hours < 72:
        return "active"
    else:
        return "active"


def format_countdown(hours: float | None) -> str:
    """Human-readable countdown."""
    if hours is None:
        return "unknown"
    if hours < 0:
        return "EXPIRED"
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes}m left"
    if hours < 24:
        return f"{hours:.1f}h left"
    days = hours / 24
    return f"{days:.1f}d left"


def verify_deal_is_live(offer: dict, source_observations: list[dict]) -> dict:
    """Verify a deal is actually live by cross-referencing sources.

    Returns verification result with confidence level.
    """
    model_id = offer.get("model_id", "")
    provider = offer.get("provider_id", "")

    # Check multiple sources for confirmation
    confirmations = []
    for obs in source_observations:
        text = obs.get("text", "").lower()
        if model_id.lower() in text or provider.lower() in text:
            confirmations.append({
                "source": obs.get("source_id", "unknown"),
                "confirmed_at": obs.get("fetched_at"),
                "confidence": 0.8,
            })

    # Check if expiry is in the past
    expires_at = offer.get("expires_at")
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_dt < datetime.now(timezone.utc):
                return {
                    "status": "expired",
                    "confidence": 0.95,
                    "reason": f"Expired at {expires_at}",
                    "confirmations": confirmations,
                }
        except (ValueError, TypeError):
            pass

    if len(confirmations) >= 2:
        confidence = min(0.95, 0.6 + len(confirmations) * 0.1)
        return {
            "status": "verified",
            "confidence": confidence,
            "reason": f"Confirmed by {len(confirmations)} sources",
            "confirmations": confirmations,
        }
    elif len(confirmations) == 1:
        return {
            "status": "partially_verified",
            "confidence": 0.6,
            "reason": "Confirmed by 1 source",
            "confirmations": confirmations,
        }
    else:
        return {
            "status": "unverified",
            "confidence": 0.3,
            "reason": "No source confirmation",
            "confirmations": [],
        }


def track_expiry(offer: dict, observations: list[dict]) -> dict:
    """Add precise expiry tracking to an offer."""
    # Parse expiry from offer metadata
    metadata = offer.get("metadata", {})
    text_for_expiry = " ".join([
        metadata.get("title", ""),
        metadata.get("excerpt", ""),
        metadata.get("note", ""),
        str(metadata.get("tos_highlights", [])),
    ])

    expiry = parse_expiry(text_for_expiry)

    # Also check if expires_at is already set
    if offer.get("expires_at") and not expiry:
        try:
            exp_dt = datetime.fromisoformat(offer["expires_at"].replace("Z", "+00:00"))
            hours = (exp_dt - datetime.now(timezone.utc)).total_seconds() / 3600
            expiry = {
                "expires_at": offer["expires_at"],
                "hours_remaining": round(hours, 1),
                "status": _status_from_hours(hours),
                "precision": "iso",
            }
        except (ValueError, TypeError):
            pass

    # Verify deal is live
    verification = verify_deal_is_live(offer, observations)

    return {
        **offer,
        "expiry": expiry or {
            "expires_at": None,
            "hours_remaining": None,
            "status": "unknown",
            "precision": "none",
        },
        "verification": verification,
        "countdown": format_countdown(
            (expiry or {}).get("hours_remaining")
        ),
    }


def enrich_offers_with_expiry(offers: list[dict], observations: list[dict] = None) -> list[dict]:
    """Add expiry tracking to all offers."""
    obs = observations or []
    enriched = []
    for offer in offers:
        enriched.append(track_expiry(offer, obs))
    return enriched


# Expiry categories for the API
EXPIRY_FILTERS = {
    "expiring_imminent": {"max_hours": 4, "label": "Expiring in < 4 hours"},
    "expiring_soon": {"max_hours": 24, "label": "Expiring in < 24 hours"},
    "expiring_week": {"max_hours": 168, "label": "Expiring in < 7 days"},
    "expired": {"max_hours": 0, "label": "Already expired"},
    "no_expiry": {"max_hours": None, "label": "No expiry tracking"},
}


def filter_by_expiry(offers: list[dict], filter_name: str) -> list[dict]:
    """Filter offers by expiry status."""
    if filter_name not in EXPIRY_FILTERS:
        return offers

    spec = EXPIRY_FILTERS[filter_name]
    result = []
    for o in offers:
        expiry = o.get("expiry", {})
        hours = expiry.get("hours_remaining")
        status = expiry.get("status", "unknown")

        if filter_name == "expired":
            if status == "expired":
                result.append(o)
        elif filter_name == "no_expiry":
            if hours is None and status != "expired":
                result.append(o)
        elif spec["max_hours"] is not None:
            if hours is not None and 0 <= hours <= spec["max_hours"]:
                result.append(o)

    return sorted(result, key=lambda x: x.get("expiry", {}).get("hours_remaining") or 9999)
