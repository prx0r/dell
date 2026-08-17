"""Oracle-1 API extensions.

Adds provenance mode and verification dimensions to API responses.
"""
from __future__ import annotations

import json
from typing import Optional


def enrich_with_provenance(offer: dict, conn) -> dict:
    """Enrich offer with provenance information."""
    from provenance import get_provenance_chain
    
    offer_id = offer.get("offer_id")
    if not offer_id:
        return offer
    
    # Add key field provenance
    provenance = {}
    for field in ["input_per_m", "output_per_m", "free", "context_tokens"]:
        if offer.get(field) is not None:
            chain = get_provenance_chain(conn, offer_id, field)
            if chain.get("status") != "NO_ASSERTION":
                provenance[field] = {
                    "state": "VERIFIED" if chain.get("observation") else "UNVERIFIED",
                    "confidence": chain.get("confidence", 0),
                    "source": chain.get("source", {}).get("source_id", "unknown"),
                }
    
    offer["provenance"] = provenance
    return offer


def enrich_with_verification(offer: dict, conn) -> dict:
    """Enrich offer with verification dimensions."""
    from verification_dimensions import get_verification_dimensions
    
    offer_id = offer.get("offer_id")
    if not offer_id:
        return offer
    
    dims = get_verification_dimensions(conn, offer_id)
    offer["verification_dimensions"] = dims
    
    # Calculate overall
    verified = sum(1 for d in dims.values() if d["status"] == "VERIFIED")
    offer["verification_summary"] = {
        "verified": verified,
        "total": len(dims),
        "status": "VERIFIED" if verified == len(dims) else "PARTIAL",
    }
    
    return offer


def enrich_with_freshness(offer: dict, conn) -> dict:
    """Enrich offer with freshness information."""
    from freshness import get_freshness_state
    
    # Check freshness for key fields
    freshness = {}
    for field in ["list_price", "availability", "context_window"]:
        observed_at = offer.get("last_verified_at") or offer.get("created_at")
        if observed_at:
            state = get_freshness_state(conn, observed_at, field, "official_api")
            freshness[field] = state
    
    offer["freshness"] = freshness
    return offer


def enrich_with_economics(offer: dict) -> dict:
    """Enrich offer with economic access classification."""
    from economics import classify_economic_access
    
    offer["economic_access"] = classify_economic_access(offer)
    return offer
