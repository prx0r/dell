"""MCP Server — Canonical implementation using SQLite.

Both REST and MCP are projections of one truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import canonical_db


def get_dataset_stats() -> dict:
    """Get dataset statistics."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    stats = {
        "total_offers": conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0],
        "free_offers": conn.execute("SELECT COUNT(*) FROM offers WHERE free = 1").fetchone()[0],
        "providers": conn.execute("SELECT COUNT(DISTINCT provider_id) FROM offers").fetchone()[0],
        "models": conn.execute("SELECT COUNT(DISTINCT model_id) FROM offers").fetchone()[0],
        "endpoints": conn.execute("SELECT COUNT(*) FROM serving_endpoints").fetchone()[0],
        "claims": conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0],
        "evidence": conn.execute("SELECT COUNT(*) FROM evidence_v2").fetchone()[0],
    }
    
    conn.close()
    return stats


def list_models(limit: int = 50, search: str = None) -> list[dict]:
    """List models."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    query = "SELECT DISTINCT model_id FROM offers"
    params = []
    
    if search:
        query += " WHERE model_id LIKE ?"
        params.append("%" + search + "%")
    
    query += " ORDER BY model_id LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    return [{"model_id": r["model_id"]} for r in rows]


def list_providers(limit: int = 50) -> list[dict]:
    """List providers."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    rows = conn.execute("""
        SELECT provider_id, COUNT(*) as offer_count
        FROM offers GROUP BY provider_id
        ORDER BY offer_count DESC LIMIT ?
    """, (limit,)).fetchall()
    
    conn.close()
    return [{"provider_id": r["provider_id"], "offers": r["offer_count"]} for r in rows]


def find_inference_deals(task: str = None, free: bool = None,
                         max_price: float = None, min_context: int = None,
                         limit: int = 50) -> list[dict]:
    """Find inference deals."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    query = "SELECT * FROM offers WHERE 1=1"
    params = []
    
    if free is not None:
        query += " AND free = ?"
        params.append(1 if free else 0)
    
    if max_price is not None:
        query += " AND (input_per_m <= ? OR input_per_m IS NULL)"
        params.append(max_price)
    
    if min_context is not None:
        query += " AND context_tokens >= ?"
        params.append(min_context)
    
    query += " ORDER BY free DESC, input_per_m ASC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    return [dict(r) for r in rows]


def recommend_model(task: str = "coding", limit: int = 5) -> dict:
    """Recommend model for task."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    # Get offers
    offers = conn.execute("""
        SELECT * FROM offers ORDER BY free DESC, input_per_m ASC LIMIT 100
    """).fetchall()
    
    conn.close()
    
    # Simple scoring
    scored = []
    for o in offers:
        score = 0
        if o["free"]:
            score += 50
        if o.get("context_tokens", 0) >= 128000:
            score += 20
        meta = json.loads(o.get("metadata_json", "{}"))
        if meta.get("tool_call"):
            score += 15
        if o.get("input_per_m") and o["input_per_m"] < 0.1:
            score += 15
        
        scored.append({"model_id": o["model_id"], "provider_id": o["provider_id"],
                       "score": score, "free": o["free"]})
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "recommendation": scored[0] if scored else None,
        "alternatives": scored[1:limit],
        "task": task,
    }


def explain_deal(offer_id: str) -> dict:
    """Explain a deal."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    offer = conn.execute("SELECT * FROM offers WHERE offer_id = ?", (offer_id,)).fetchone()
    if not offer:
        conn.close()
        return {"error": "Offer not found"}
    
    # Get claims
    claims = conn.execute("SELECT * FROM claims WHERE offer_id = ?", (offer_id,)).fetchall()
    
    # Get evidence
    evidence = conn.execute("""
        SELECT e.* FROM evidence_v2 e
        JOIN claims c ON e.claim_id = c.claim_id
        WHERE c.offer_id = ?
    """, (offer_id,)).fetchall()
    
    conn.close()
    
    return {
        "offer_id": offer_id,
        "model_id": offer["model_id"],
        "provider_id": offer["provider_id"],
        "free": offer["free"],
        "claims_count": len(claims),
        "evidence_count": len(evidence),
    }


def get_deal_changes(offer_id: str, limit: int = 50) -> list[dict]:
    """Get deal history."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    rows = conn.execute("""
        SELECT * FROM deal_events WHERE offer_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (offer_id, limit)).fetchall()
    
    conn.close()
    return [dict(r) for r in rows]
