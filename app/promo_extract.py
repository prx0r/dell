"""Deterministic promotion extraction from text using regex patterns."""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PATTERNS = [
    {
        "regex": r"(\d+(?:\.\d+)?)\s*%\s*off",
        "event_type": "discount_percent",
        "confidence": 0.95,
        "extract": lambda m: {"discount_percent": float(m.group(1))},
    },
    {
        "regex": r"free\s+for\s+(\d+)\s*(days?|months?|hours?|weeks?)",
        "event_type": "temporary_free",
        "confidence": 0.95,
        "extract": lambda m: {"free_duration": int(m.group(1)), "free_unit": m.group(2).lower()},
    },
    {
        "regex": r"limited\s+time",
        "event_type": "limited_time",
        "confidence": 0.7,
        "extract": lambda m: {"note": "limited time offer"},
    },
    {
        "regex": r"launch\s+pric(?:e|ing)",
        "event_type": "launch_pricing",
        "confidence": 0.85,
        "extract": lambda m: {"note": "launch pricing"},
    },
    {
        "regex": r"(\d+)x\s+(?:usage|tokens?|requests?|calls?)",
        "event_type": "multiplier",
        "confidence": 0.9,
        "extract": lambda m: {"multiplier": int(m.group(1))},
    },
    {
        "regex": r"signup\s+credit",
        "event_type": "signup_credit",
        "confidence": 0.85,
        "extract": lambda m: {"note": "signup credit"},
    },
    {
        "regex": r"off[- ]peak",
        "event_type": "off_peak",
        "confidence": 0.9,
        "extract": lambda m: {"note": "off-peak pricing"},
    },
    {
        "regex": r"promo\s+ends?\s+(\w+\s+\d+(?:,?\s*\d{4})?)",
        "event_type": "promo_expiry",
        "confidence": 0.9,
        "extract": lambda m: {"expiry_date": m.group(1)},
    },
    {
        "regex": r"extended?\s+through\s+(\w+\s+\d+(?:,?\s*\d{4})?)",
        "event_type": "promo_extended",
        "confidence": 0.9,
        "extract": lambda m: {"extended_through": m.group(1)},
    },
    {
        "regex": r"\$(\d+(?:\.\d+)?)\s*/?\s*(?:mo(?:nth)?|year|yr|annual)",
        "event_type": "price_mention",
        "confidence": 0.9,
        "extract": lambda m: {"price_usd": float(m.group(1))},
    },
    {
        "regex": r"\$(\d+(?:\.\d+)?)\s*(?:credit|free\s+credit)",
        "event_type": "credit_amount",
        "confidence": 0.85,
        "extract": lambda m: {"credit_usd": float(m.group(1))},
    },
    {
        "regex": r"(\d+[kK]?)\s*(?:tokens?|credits?)\s*(?:free|bonus|included)",
        "event_type": "token_bonus",
        "confidence": 0.85,
        "extract": lambda m: {"token_bonus": m.group(1)},
    },
]


def extract_promotions(text: str, source_id: str) -> list[dict]:
    """Extract promotion signals from text using regex patterns.

    Args:
        text: Raw text content to scan for promotions.
        source_id: Identifier for the source this text came from.

    Returns:
        List of promotion event dicts with fields:
            event_type, confidence, details, source_id, matched_text
    """
    if not text or not isinstance(text, str):
        logger.warning("Empty or invalid text provided for extraction from source %s", source_id)
        return []

    events: list[dict] = []
    text_lower = text.lower()

    for pattern in PATTERNS:
        try:
            for match in re.finditer(pattern["regex"], text_lower):
                details = pattern["extract"](match)
                event = {
                    "event_type": pattern["event_type"],
                    "confidence": pattern["confidence"],
                    "details": details,
                    "source_id": source_id,
                    "matched_text": match.group(0),
                }
                events.append(event)
                logger.debug(
                    "Extracted %s from source %s: %s",
                    event["event_type"],
                    source_id,
                    details,
                )
        except Exception as exc:
            logger.error(
                "Pattern %s failed on source %s: %s",
                pattern["event_type"],
                source_id,
                exc,
            )

    logger.info("Extracted %d promotion events from source %s", len(events), source_id)
    return events
