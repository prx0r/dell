"""Verification run management — first-class object for tracking verification state."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

import canonical_db


# Verification ladder levels
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
    """Complete a verification run with results."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        UPDATE verification_runs SET
            completed_at = ?,
            sources_attempted = ?,
            sources_successful = ?,
            sources_failed = ?,
            claims_confirmed = ?,
            claims_created = ?,
            claims_invalidated = ?,
            status = 'completed'
        WHERE run_id = ?
    """, (now, result.get("sources_attempted", 0), result.get("sources_successful", 0),
          result.get("sources_failed", 0), result.get("claims_confirmed", 0),
          result.get("claims_created", 0), result.get("claims_invalidated", 0), run_id))
    conn.commit()


def record_tool_event(conn, run_id: str, tool: str, arguments: dict = None,
                      result_data: dict = None, parent_hash: str = None) -> str:
    """Record a tool event in the append-only hash chain."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Get next sequence number
    row = conn.execute("SELECT MAX(seq) FROM tool_events WHERE verification_run_id = ?",
                       (run_id,)).fetchone()
    seq = (row[0] or 0) + 1

    # Compute hashes
    args_hash = hashlib.sha256(json.dumps(arguments or {}, sort_keys=True).encode()).hexdigest()
    result_hash = hashlib.sha256(json.dumps(result_data or {}, sort_keys=True).encode()).hexdigest()

    # Compute event hash (chain with parent)
    event_data = "%s:%d:%s:%s:%s" % (run_id, seq, tool, args_hash, result_hash)
    event_hash = hashlib.sha256(event_data.encode()).hexdigest()

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute("""
        INSERT INTO tool_events (seq, verification_run_id, tool, arguments_hash,
            result_hash, status, parent_event_hash, event_hash, created_at)
        VALUES (?, ?, ?, ?, ?, 'success', ?, ?, ?)
    """, (seq, run_id, tool, args_hash, result_hash, parent_hash, event_hash, now))
    conn.commit()
    return event_hash


def compute_run_root(conn, run_id: str) -> str:
    """Compute Merkle root for a verification run."""
    # Get all tool event hashes for this run
    rows = conn.execute(
        "SELECT event_hash FROM tool_events WHERE verification_run_id = ? ORDER BY seq",
        (run_id,)).fetchall()
    if not rows:
        return hashlib.sha256(b"empty").hexdigest()

    # Build Merkle tree
    hashes = [r[0] for r in rows]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
                  for i in range(0, len(hashes), 2)]

    return hashes[0] if hashes else hashlib.sha256(b"empty").hexdigest()


def get_verification_status(conn, offer_id: str) -> dict:
    """Get verification status for an offer."""
    # Count claims for this offer
    claims = conn.execute(
        "SELECT COUNT(*) FROM claims WHERE offer_id = ?", (offer_id,)).fetchone()[0]

    # Count evidence
    evidence = conn.execute(
        "SELECT COUNT(*) FROM evidence_v2 WHERE claim_id IN (SELECT claim_id FROM claims WHERE offer_id = ?)",
        (offer_id,)).fetchone()[0]

    # Get latest verification run
    run = conn.execute(
        "SELECT run_id, status, completed_at FROM verification_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()

    return {
        "offer_id": offer_id,
        "claims_count": claims,
        "evidence_count": evidence,
        "latest_run": dict(run) if run else None,
        "verification_level": VERIFICATION_LEVELS[min(claims, len(VERIFICATION_LEVELS) - 1)],
    }


# Verification ladder
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
