"""Query Service — Shared service for REST and MCP.

Both REST and MCP call this service.
No independent scoring logic.
"""
from __future__ import annotations

import json
from typing import Optional

import canonical_db


def search_routes(task: str = None, free: bool = None, 
                  max_price: float = None, min_context: int = None,
                  limit: int = 50) -> list[dict]:
    """Search for routes. Used by both REST and MCP."""
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


def get_dataset_stats() -> dict:
    """Get dataset statistics. Used by both REST and MCP."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    stats = {
        "total_offers": conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0],
        "free_offers": conn.execute("SELECT COUNT(*) FROM offers WHERE free = 1").fetchone()[0],
        "providers": conn.execute("SELECT COUNT(DISTINCT provider_id) FROM offers").fetchone()[0],
        "models": conn.execute("SELECT COUNT(DISTINCT model_id) FROM offers").fetchone()[0],
        "endpoints": conn.execute("SELECT COUNT(*) FROM serving_endpoints").fetchone()[0],
    }
    
    conn.close()
    return stats


def list_models(limit: int = 50, search: str = None) -> list[dict]:
    """List models. Used by both REST and MCP."""
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
    """List providers. Used by both REST and MCP."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    rows = conn.execute("""
        SELECT provider_id, COUNT(*) as offer_count
        FROM offers GROUP BY provider_id
        ORDER BY offer_count DESC LIMIT ?
    """, (limit,)).fetchall()
    
    conn.close()
    return [{"provider_id": r["provider_id"], "offers": r["offer_count"]} for r in rows]


def explain_route(offer_id: str) -> dict:
    """Explain a route. Used by both REST and MCP."""
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
