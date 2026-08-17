"""Freshness checking for claims and observations.

Each claim type has a TTL based on source type.
Claims expire when now > observed_at + TTL.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta


# Default TTLs if no policy exists
DEFAULT_TTLS = {
    "model_author": 365 * 24 * 3600,  # 1 year
    "context_window": 30 * 24 * 3600,  # 30 days
    "list_price": 24 * 3600,  # 1 day
    "flash_promo": 3600,  # 1 hour
    "availability": 300,  # 5 minutes
    "throughput": 60,  # 1 minute
    "rate_limit": 24 * 3600,  # 1 day
    "endpoint_reachable": 60,  # 1 minute
}


def get_ttl(conn, claim_type: str, source_type: str) -> int:
    """Get TTL for a claim type from policy or default."""
    row = conn.execute("""
        SELECT ttl_seconds FROM freshness_policies
        WHERE claim_type = ? AND source_type = ?
    """, (claim_type, source_type)).fetchone()
    
    if row:
        return row[0]
    
    return DEFAULT_TTLS.get(claim_type, 86400)  # Default 1 day


def is_fresh(conn, observed_at: str, claim_type: str, source_type: str) -> bool:
    """Check if a claim is still fresh based on its policy."""
    if not observed_at:
        return False
    
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        ttl = get_ttl(conn, claim_type, source_type)
        expires = observed + timedelta(seconds=ttl)
        return datetime.now(observed.tzinfo) < expires
    except:
        return False


def get_freshness_state(conn, observed_at: str, claim_type: str, source_type: str) -> str:
    """Get freshness state: FRESH, STALE, or UNKNOWN."""
    if not observed_at:
        return "UNKNOWN"
    
    if is_fresh(conn, observed_at, claim_type, source_type):
        return "FRESH"
    
    return "STALE"


def record_negative_observation(conn, observation_id: int, model_id: str,
                                 field: str, absence_type: str,
                                 source_url: str = None, details: str = None):
    """Record that a field was NOT found in an observation.
    
    absence_type:
    - MODEL_ABSENT: model not listed
    - FIELD_ABSENT: field not present
    - PRICE_ABSENT: no price listed
    - QUOTA_ABSENT: no quota listed
    - PROMO_ABSENT: no promotion found
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO negative_observations (observation_id, model_id, field,
            absence_type, checked_at, source_url, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (observation_id, model_id, field, absence_type, now, source_url, details, now))
