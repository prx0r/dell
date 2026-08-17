"""Verification dimensions for Oracle-1.

Verification is multidimensional, not a single ladder.
Each dimension is independent.
"""
from __future__ import annotations

import json
import time
from typing import Optional


# Verification dimensions
DIMENSIONS = {
    "pricing_claim": "Price information verified",
    "endpoint_reachable": "Endpoint is reachable",
    "model_listed": "Model is listed on provider",
    "inference_success": "Inference canary succeeded",
    "quota_condition": "Quota conditions verified",
    "promotion_active": "Promotion is currently active",
    "context_window": "Context window verified",
    "tool_support": "Tool calling support verified",
    "rate_limit": "Rate limit verified",
    "availability": "Endpoint availability verified",
}


def get_verification_dimensions(conn, offer_id: str) -> dict:
    """Get all verification dimensions for an offer."""
    result = {}
    
    for dim in DIMENSIONS:
        row = conn.execute("""
            SELECT status, checked_at, confidence, details
            FROM verification_dimensions
            WHERE offer_id = ? AND dimension = ?
            ORDER BY checked_at DESC LIMIT 1
        """, (offer_id, dim)).fetchone()
        
        if row:
            result[dim] = {
                "status": row["status"],
                "checked_at": row["checked_at"],
                "confidence": row["confidence"],
                "details": row["details"],
            }
        else:
            result[dim] = {
                "status": "UNKNOWN",
                "checked_at": None,
                "confidence": 0.0,
                "details": None,
            }
    
    return result


def set_verification_dimension(conn, offer_id: str, dimension: str,
                                status: str, confidence: float = 0.5,
                                details: str = None):
    """Set a verification dimension."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    conn.execute("""
        INSERT INTO verification_dimensions (offer_id, dimension, status,
            checked_at, confidence, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (offer_id, dimension, status, now, confidence, details, now))
    conn.commit()


def get_overall_verification(conn, offer_id: str) -> dict:
    """Get overall verification status."""
    dims = get_verification_dimensions(conn, offer_id)
    
    # Count verified dimensions
    verified = sum(1 for d in dims.values() if d["status"] == "VERIFIED")
    unknown = sum(1 for d in dims.values() if d["status"] == "UNKNOWN")
    failed = sum(1 for d in dims.values() if d["status"] == "FAILED")
    
    total = len(dims)
    
    return {
        "offer_id": offer_id,
        "dimensions": dims,
        "summary": {
            "total": total,
            "verified": verified,
            "unknown": unknown,
            "failed": failed,
        },
        "overall_status": "VERIFIED" if verified == total else
                         "FAILED" if failed > 0 else
                         "PARTIAL" if verified > 0 else "UNKNOWN",
    }
