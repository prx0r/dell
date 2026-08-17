"""Verification run management — first-class object for tracking verification state.

This is the proof kernel. Every claim must be backed by evidence.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

import canonical_db


# Verification ladder levels — these are PREDICATES, not ordinal points
VERIFICATION_LEVELS = [
    "LEAD",
    "SOURCE_FETCHED",
    "CLAIM_EXTRACTED",
    "PRIMARY_EVIDENCE",
    "PRIMARY_CORROBORATED",
    "ENDPOINT_REACHABLE",
    "MODEL_LISTED",
    "INFERENCE_SUCCEEDED",
    "DEAL_CONDITION_CONFIRMED",
]

# Required evidence for each level
VERIFICATION_PREDICATES = {
    "LEAD": {"claims": 0, "evidence": 0},
    "SOURCE_FETCHED": {"claims": 0, "evidence": 0, "requires_observation": True},
    "CLAIM_EXTRACTED": {"claims": 1, "evidence": 0},
    "PRIMARY_EVIDENCE": {"claims": 1, "evidence": 1, "requires_primary": True},
    "PRIMARY_CORROBORATED": {"claims": 2, "evidence": 2, "requires_primary": True, "requires_corroboration": True},
    "ENDPOINT_REACHABLE": {"requires_reachability_check": True},
    "MODEL_LISTED": {"requires_model_listing": True},
    "INFERENCE_SUCCEEDED": {"requires_inference_canary": True},
    "DEAL_CONDITION_CONFIRMED": {"requires_deal_test": True},
}


def create_verification_run(conn, run_type: str = "DEEP_VERIFY",
                            agent_model: str = None, skill_id: str = None) -> str:
    """Create a new verification run."""
    run_id = "vr_%s_%s" % (time.strftime("%Y%m%d_%H%M%S"), hashlib.sha256(str(time.time()).encode()).hexdigest()[:8])
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO verification_runs (run_id, run_type, started_at, agent_model, skill_id, status)
        VALUES (?, ?, ?, ?, ?, 'started')
    """, (run_id, run_type, now, agent_model, skill_id))
    conn.commit()
    return run_id


def complete_verification_run(conn, run_id: str, result: dict):
    """Complete a verification run with results.
    
    This seals the run with cryptographic proof.
    After SEALED, no child artifacts can be modified.
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Compute all Merkle roots
    event_merkle_root = compute_event_merkle_root(conn, run_id)
    artifact_merkle_root = compute_artifact_merkle_root(conn, run_id)
    claim_merkle_root = compute_claim_merkle_root(conn, run_id)
    evidence_merkle_root = compute_evidence_merkle_root(conn, run_id)
    
    # Compute run root
    run_root = compute_run_root(conn, run_id)
    
    # Get previous run root for chaining
    prev_run = conn.execute(
        "SELECT run_root FROM verification_runs WHERE run_id != ? ORDER BY completed_at DESC LIMIT 1",
        (run_id,)
    ).fetchone()
    previous_run_root = prev_run[0] if prev_run else None
    
    # Compute event log hash
    event_log_hash = compute_event_log_hash(conn, run_id)
    
    conn.execute("""
        UPDATE verification_runs SET
            completed_at = ?,
            sources_attempted = ?,
            sources_successful = ?,
            sources_failed = ?,
            claims_confirmed = ?,
            claims_created = ?,
            claims_invalidated = ?,
            previous_run_root = ?,
            event_log_hash = ?,
            artifact_merkle_root = ?,
            claim_merkle_root = ?,
            run_root = ?,
            status = 'sealed'
        WHERE run_id = ?
    """, (now, result.get("sources_attempted", 0), result.get("sources_successful", 0),
          result.get("sources_failed", 0), result.get("claims_confirmed", 0),
          result.get("claims_created", 0), result.get("claims_invalidated", 0),
          previous_run_root, event_log_hash, artifact_merkle_root,
          claim_merkle_root, run_root, run_id))
    conn.commit()


def record_tool_event(conn, run_id: str, tool: str, arguments: dict = None,
                      result_data: dict = None) -> str:
    """Record a tool event in the append-only hash chain.
    
    Parent hash is automatically determined from the previous event.
    Agent never touches it.
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Get next sequence number
    row = conn.execute("SELECT MAX(seq) FROM tool_events WHERE verification_run_id = ?",
                       (run_id,)).fetchone()
    seq = (row[0] or 0) + 1
    
    # Get parent hash from previous event (determined by runtime, not agent)
    parent_row = conn.execute(
        "SELECT event_hash FROM tool_events WHERE verification_run_id = ? ORDER BY seq DESC LIMIT 1",
        (run_id,)
    ).fetchone()
    parent_hash = parent_row[0] if parent_row else None
    
    # Compute hashes
    args_hash = hashlib.sha256(json.dumps(arguments or {}, sort_keys=True).encode()).hexdigest()
    result_hash = hashlib.sha256(json.dumps(result_data or {}, sort_keys=True).encode()).hexdigest()
    
    # Compute event hash including parent (cryptographic chain)
    event_data = "%s:%d:%s:%s:%s:%s" % (run_id, seq, tool, args_hash, result_hash, parent_hash or "genesis")
    event_hash = hashlib.sha256(event_data.encode()).hexdigest()
    
    conn.execute("""
        INSERT INTO tool_events (seq, verification_run_id, tool, arguments_hash,
            result_hash, status, parent_event_hash, event_hash, created_at)
        VALUES (?, ?, ?, ?, ?, 'success', ?, ?, ?)
    """, (seq, run_id, tool, args_hash, result_hash, parent_hash, event_hash, now))
    conn.commit()
    return event_hash


def compute_event_merkle_root(conn, run_id: str) -> str:
    """Compute Merkle root for tool events."""
    rows = conn.execute(
        "SELECT event_hash FROM tool_events WHERE verification_run_id = ? ORDER BY seq",
        (run_id,)).fetchall()
    if not rows:
        return hashlib.sha256(b"empty_events").hexdigest()
    
    hashes = [r[0] for r in rows]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
                  for i in range(0, len(hashes), 2)]
    
    return hashes[0]


def compute_artifact_merkle_root(conn, run_id: str) -> str:
    """Compute Merkle root for artifacts used in this run."""
    rows = conn.execute("""
        SELECT DISTINCT artifact_id FROM evidence_v2 
        WHERE verification_run_id = ? AND artifact_id IS NOT NULL
    """, (run_id,)).fetchall()
    
    if not rows:
        return hashlib.sha256(b"empty_artifacts").hexdigest()
    
    hashes = [r[0] for r in rows]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
                  for i in range(0, len(hashes), 2)]
    
    return hashes[0]


def compute_claim_merkle_root(conn, run_id: str) -> str:
    """Compute Merkle root for claims created in this run."""
    rows = conn.execute("""
        SELECT claim_id, offer_id, claim_type, claim_value 
        FROM claims WHERE created_at >= (
            SELECT started_at FROM verification_runs WHERE run_id = ?
        ) AND created_at <= (
            SELECT COALESCE(completed_at, datetime('now')) FROM verification_runs WHERE run_id = ?
        )
    """, (run_id, run_id)).fetchall()
    
    if not rows:
        return hashlib.sha256(b"empty_claims").hexdigest()
    
    claim_hashes = []
    for r in rows:
        claim_data = f"{r[0]}:{r[1]}:{r[2]}:{r[3]}"
        claim_hashes.append(hashlib.sha256(claim_data.encode()).hexdigest())
    
    while len(claim_hashes) > 1:
        if len(claim_hashes) % 2 == 1:
            claim_hashes.append(claim_hashes[-1])
        claim_hashes = [hashlib.sha256((claim_hashes[i] + claim_hashes[i+1]).encode()).hexdigest()
                        for i in range(0, len(claim_hashes), 2)]
    
    return claim_hashes[0]


def compute_evidence_merkle_root(conn, run_id: str) -> str:
    """Compute Merkle root for evidence records."""
    rows = conn.execute("""
        SELECT evidence_id, claim_id, artifact_id, selector 
        FROM evidence_v2 WHERE verification_run_id = ?
    """, (run_id,)).fetchall()
    
    if not rows:
        return hashlib.sha256(b"empty_evidence").hexdigest()
    
    ev_hashes = []
    for r in rows:
        ev_data = f"{r[0]}:{r[1]}:{r[2]}:{r[3]}"
        ev_hashes.append(hashlib.sha256(ev_data.encode()).hexdigest())
    
    while len(ev_hashes) > 1:
        if len(ev_hashes) % 2 == 1:
            ev_hashes.append(ev_hashes[-1])
        ev_hashes = [hashlib.sha256((ev_hashes[i] + ev_hashes[i+1]).encode()).hexdigest()
                     for i in range(0, len(ev_hashes), 2)]
    
    return ev_hashes[0]


def compute_event_log_hash(conn, run_id: str) -> str:
    """Compute hash of all events in this run."""
    rows = conn.execute(
        "SELECT event_hash FROM tool_events WHERE verification_run_id = ? ORDER BY seq",
        (run_id,)).fetchall()
    
    if not rows:
        return hashlib.sha256(b"empty_log").hexdigest()
    
    combined = "".join(r[0] for r in rows)
    return hashlib.sha256(combined.encode()).hexdigest()


def compute_run_root(conn, run_id: str) -> str:
    """Compute the complete run root binding all Merkle roots.
    
    run_root = SHA256(
        proof_version || previous_run_root || event_merkle_root || 
        artifact_merkle_root || claim_merkle_root || evidence_merkle_root
    )
    """
    # Get run info
    run = conn.execute(
        "SELECT previous_run_root FROM verification_runs WHERE run_id = ?",
        (run_id,)
    ).fetchone()
    previous_run_root = run[0] if run else None
    
    # Compute all roots
    event_root = compute_event_merkle_root(conn, run_id)
    artifact_root = compute_artifact_merkle_root(conn, run_id)
    claim_root = compute_claim_merkle_root(conn, run_id)
    evidence_root = compute_evidence_merkle_root(conn, run_id)
    
    # Build run root
    proof_version = "1.0"
    run_root_data = "%s:%s:%s:%s:%s:%s" % (
        proof_version,
        previous_run_root or "genesis",
        event_root,
        artifact_root,
        claim_root,
        evidence_root,
    )
    
    return hashlib.sha256(run_root_data.encode()).hexdigest()


def get_verification_status(conn, offer_id: str) -> dict:
    """Get verification status for an offer.
    
    Verification level is derived from actual completed VerificationChecks,
    NOT from claim count.
    """
    # Count claims for this offer
    claims = conn.execute(
        "SELECT COUNT(*) FROM claims WHERE offer_id = ?", (offer_id,)).fetchone()[0]
    
    # Count evidence
    evidence = conn.execute(
        "SELECT COUNT(*) FROM evidence_v2 WHERE claim_id IN (SELECT claim_id FROM claims WHERE offer_id = ?)",
        (offer_id,)).fetchone()[0]
    
    # Get actual verification checks
    checks = conn.execute(
        "SELECT check_type, status, checked_at FROM verification_checks WHERE offer_id = ? ORDER BY checked_at DESC",
        (offer_id,)
    ).fetchall()
    
    # Determine verification level from actual checks
    verification_level = "LEAD"
    
    has_observation = conn.execute(
        "SELECT COUNT(*) FROM source_observations WHERE source_id IN (SELECT source_id FROM offers WHERE offer_id = ?)",
        (offer_id,)
    ).fetchone()[0] > 0
    
    # Check for actual verification checks
    has_reachability = any(c["check_type"] == "REACHABILITY" and c["status"] == "OK" for c in checks)
    has_model_listing = any(c["check_type"] == "MODEL_LISTING" and c["status"] == "OK" for c in checks)
    has_inference = any(c["check_type"] == "INFERENCE_CANARY" and c["status"] == "OK" for c in checks)
    has_deal_test = any(c["check_type"] == "DEAL_CONDITION" and c["status"] == "OK" for c in checks)
    
    # Check for primary evidence verification
    has_primary_check = any(c["check_type"] == "PRIMARY_EVIDENCE" and c["status"] == "OK" for c in checks)
    has_corroboration_check = any(c["check_type"] == "PRIMARY_CORROBORATED" and c["status"] == "OK" for c in checks)
    
    # Level is determined by ACTUAL verification checks, NOT evidence count
    if has_observation:
        verification_level = "SOURCE_FETCHED"
    if evidence > 0:
        verification_level = "CLAIM_EXTRACTED"  # Can have evidence without verification
    if has_primary_check:
        verification_level = "PRIMARY_EVIDENCE"
    if has_corroboration_check:
        verification_level = "PRIMARY_CORROBORATED"
    if has_reachability:
        verification_level = "ENDPOINT_REACHABLE"
    if has_model_listing:
        verification_level = "MODEL_LISTED"
    if has_inference:
        verification_level = "INFERENCE_SUCCEEDED"
    if has_deal_test:
        verification_level = "DEAL_CONDITION_CONFIRMED"
    
    # Get latest verification run
    run = conn.execute(
        "SELECT run_id, status, completed_at, run_root FROM verification_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    
    # Get latest check time
    latest_check = checks[0]["checked_at"] if checks else None
    
    return {
        "offer_id": offer_id,
        "claims_count": claims,
        "evidence_count": evidence,
        "latest_run": dict(run) if run else None,
        "verification_level": verification_level,
        "checks": [dict(c) for c in checks],
        "latest_check_at": latest_check,
    }
