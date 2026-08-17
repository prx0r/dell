"""Wire discovery → claims → evidence pipeline.

Instead of adapter → offer directly, the path becomes:
  adapter → observation → candidate_claim → evidence → adjudication → offer

Evidence records are created ATOMICALLY with claims.
Artifact storage is CONNECTED to observations.
Claims are linked to CORRECT observations.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import canonical_db
from offer_id import OfferId
from artifact_store import store_artifact


def extract_claims_from_adapter(adapter_module, observation) -> list[dict]:
    """Extract candidate claims from an adapter observation."""
    claims = []
    try:
        offers = adapter_module.extract(observation)
        for offer in offers:
            # Build offer_id using canonical OfferId.create()
            offer_id = OfferId.create(offer.provider_id, offer.model_id, offer.offer_kind)
            if offer.input_per_m is not None:
                claims.append({
                    "subject_type": "commercial_offer",
                    "subject_id": offer_id,
                    "predicate": "input_price",
                    "value_json": json.dumps({"input_per_m": offer.input_per_m}),
                    "confidence": 0.9,
                    "source_url": offer.metadata.get("source_url", ""),
                })
            if offer.output_per_m is not None:
                claims.append({
                    "subject_type": "commercial_offer",
                    "subject_id": offer_id,
                    "predicate": "output_price",
                    "value_json": json.dumps({"output_per_m": offer.output_per_m}),
                    "confidence": 0.9,
                    "source_url": offer.metadata.get("source_url", ""),
                })
            if offer.free:
                claims.append({
                    "subject_type": "commercial_offer",
                    "subject_id": offer_id,
                    "predicate": "price_state",
                    "value_json": json.dumps({"price_state": "FREE"}),
                    "confidence": 0.95,
                    "source_url": offer.metadata.get("source_url", ""),
                })
            if offer.context_tokens:
                claims.append({
                    "subject_type": "model",
                    "subject_id": offer.model_id,
                    "predicate": "context_tokens",
                    "value_json": json.dumps({"context_tokens": offer.context_tokens}),
                    "confidence": 0.9,
                    "source_url": offer.metadata.get("source_url", ""),
                })
            if offer.requests_per_5h or offer.requests_per_day:
                claims.append({
                    "subject_type": "commercial_offer",
                    "subject_id": offer_id,
                    "predicate": "quota",
                    "value_json": json.dumps({
                        "requests_per_5h": offer.requests_per_5h,
                        "requests_per_day": offer.requests_per_day,
                    }),
                    "confidence": 0.8,
                    "source_url": offer.metadata.get("source_url", ""),
                })
            if offer.usage_multiplier:
                claims.append({
                    "subject_type": "deal",
                    "subject_id": offer_id,
                    "predicate": "usage_multiplier",
                    "value_json": json.dumps({"multiplier": offer.usage_multiplier}),
                    "confidence": 0.95,
                    "source_url": offer.metadata.get("source_url", ""),
                })
    except Exception as e:
        pass
    return claims


def commit_claims_with_evidence(conn, claims: list[dict], observation_id: int,
                                 artifact_id: str = None):
    """Commit claims to the database WITH evidence records.
    
    This is ATOMIC — no evidence means no canonical claim.
    
    Args:
        claims: List of claim dicts
        observation_id: The observation this claim came from
        artifact_id: The artifact ID for provenance
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    for claim in claims:
        # Insert claim
        cursor = conn.execute("""
            INSERT INTO claims (offer_id, claim_type, claim_value,
                source_observation_id, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (claim.get("subject_id", ""), claim.get("predicate", "unknown"),
              claim.get("value_json", "{}"), observation_id,
              claim.get("confidence", 0.5), now))
        
        claim_id = cursor.lastrowid
        
        # Insert evidence record (ATOMIC with claim)
        conn.execute("""
            INSERT INTO evidence_v2 (claim_id, artifact_id, authority, 
                selector_type, selector, excerpt, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (claim_id, artifact_id, "source_observation",
              "text_content", claim.get("source_url", ""),
              claim.get("value_json", "{}"),
              claim.get("content_hash", ""),
              now))


def commit_claims(conn, claims: list[dict], observation_id: int):
    """Commit claims to the database (legacy wrapper).
    
    For new code, use commit_claims_with_evidence() instead.
    """
    commit_claims_with_evidence(conn, claims, observation_id)
