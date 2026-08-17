"""Provenance chain for Oracle-1.

Every served factual value must trace to:
  served field → offer_assertion → claim → source_observation → raw artifact → source
"""
from __future__ import annotations

import json
import time
from typing import Optional


def get_provenance_chain(conn, offer_id: str, field: str) -> dict:
    """Get the full provenance chain for a field value."""
    
    # 1. Get the assertion
    assertion = conn.execute("""
        SELECT assertion_id, normalized_value, claim_id, observation_id,
               valid_from, valid_until, confidence, authority, state
        FROM offer_assertions
        WHERE offer_id = ? AND field = ? AND state = 'active'
        ORDER BY created_at DESC LIMIT 1
    """, (offer_id, field)).fetchone()
    
    if not assertion:
        return {"field": field, "status": "NO_ASSERTION"}
    
    result = {
        "field": field,
        "assertion_id": assertion["assertion_id"],
        "value": assertion["normalized_value"],
        "valid_from": assertion["valid_from"],
        "valid_until": assertion["valid_until"],
        "confidence": assertion["confidence"],
        "authority": assertion["authority"],
        "state": assertion["state"],
    }
    
    # 2. Get the claim
    if assertion["claim_id"]:
        claim = conn.execute("""
            SELECT claim_id, claim_type, claim_value, confidence, source_observation_id
            FROM claims WHERE claim_id = ?
        """, (assertion["claim_id"],)).fetchone()
        
        if claim:
            result["claim"] = {
                "claim_id": claim["claim_id"],
                "type": claim["claim_type"],
                "value": claim["claim_value"],
                "confidence": claim["confidence"],
            }
            
            # 3. Get the observation
            if claim["source_observation_id"]:
                obs = conn.execute("""
                    SELECT observation_id, source_id, url, fetched_at,
                           http_status, content_hash
                    FROM source_observations
                    WHERE observation_id = ?
                """, (claim["source_observation_id"],)).fetchone()
                
                if obs:
                    result["observation"] = {
                        "observation_id": obs["observation_id"],
                        "source_id": obs["source_id"],
                        "url": obs["url"],
                        "fetched_at": obs["fetched_at"],
                        "http_status": obs["http_status"],
                        "content_hash": obs["content_hash"],
                    }
                    
                    # 4. Get source info
                    source = conn.execute("""
                        SELECT source_id, adapter_module
                        FROM sources WHERE source_id = ?
                    """, (obs["source_id"],)).fetchone()
                    
                    if source:
                        result["source"] = {
                            "source_id": source["source_id"],
                            "adapter": source["adapter_module"],
                        }
    
    return result


def verify_provenance_exists(conn, offer_id: str, field: str) -> bool:
    """Verify that a field has a complete provenance chain."""
    chain = get_provenance_chain(conn, offer_id, field)
    
    # Must have assertion, claim, observation, and source
    return all(key in chain for key in ["assertion_id", "claim", "observation", "source"])


def get_all_unproven_fields(conn) -> list[dict]:
    """Find all served fields without provenance."""
    # Get all offers with values
    offers = conn.execute("""
        SELECT offer_id, input_per_m, output_per_m, free, context_tokens
        FROM offers WHERE lifecycle_state = 'ACTIVE_VERIFIED'
    """).fetchall()
    
    unproven = []
    for offer in offers:
        fields_to_check = []
        if offer["input_per_m"] is not None:
            fields_to_check.append("input_per_m")
        if offer["output_per_m"] is not None:
            fields_to_check.append("output_per_m")
        if offer["free"]:
            fields_to_check.append("free")
        if offer["context_tokens"] is not None:
            fields_to_check.append("context_tokens")
        
        for field in fields_to_check:
            if not verify_provenance_exists(conn, offer["offer_id"], field):
                unproven.append({
                    "offer_id": offer["offer_id"],
                    "field": field,
                })
    
    return unproven
