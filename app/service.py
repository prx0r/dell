"""DealService — one service powering REST, MCP, and site.

All surfaces call this. No direct snapshot reading elsewhere.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import canonical_db
from identity import normalize_model_name, infer_relationship, can_transfer_field


class DealService:
    """Canonical service layer for LLM Deals."""

    def __init__(self):
        self._conn = None

    def _get_conn(self):
        if self._conn is None:
            self._conn = canonical_db.connect()
            canonical_db.migrate(self._conn)
        return self._conn

    def list_models(self, search: str = None, limit: int = 50) -> list[dict]:
        """List unique models with their best offer data."""
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT model_id FROM offers WHERE model_id IS NOT NULL").fetchall()
        models = []
        for row in rows:
            mid = row["model_id"]
            if search and search.lower() not in mid.lower():
                continue
            # Get best offer for this model
            best = conn.execute(
                "SELECT * FROM offers WHERE model_id = ? ORDER BY free DESC, context_tokens DESC LIMIT 1",
                (mid,)
            ).fetchone()
            if best:
                o = dict(best)
                meta = json.loads(o.get("metadata_json", "{}"))
                models.append({
                    "model_id": mid,
                    "providers": [r["provider_id"] for r in conn.execute(
                        "SELECT DISTINCT provider_id FROM offers WHERE model_id = ?", (mid,)).fetchall()],
                    "cheapest_input": o.get("input_per_m"),
                    "context_tokens": o.get("context_tokens"),
                    "free_available": bool(o.get("free")),
                    "tool_calling": meta.get("tool_call"),
                })
        return models[:limit]

    def get_model(self, model_id: str) -> dict:
        """Get all offers for a specific model across providers."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM offers WHERE model_id = ?", (model_id,)).fetchall()
        offers = []
        for r in rows:
            o = dict(r)
            o["metadata"] = json.loads(o.get("metadata_json", "{}"))
            offers.append(o)
        return {"model_id": model_id, "offerings": offers, "count": len(offers)}

    def list_deals(self, free: bool = None, max_price: float = None,
                   tool_calling: bool = None, limit: int = 50) -> list[dict]:
        """List deals with filters."""
        conn = self._get_conn()
        query = "SELECT * FROM offers WHERE 1=1"
        params = []
        if free is not None:
            query += " AND free = ?"
            params.append(int(free))
        if max_price is not None:
            query += " AND input_per_m IS NOT NULL AND input_per_m <= ?"
            params.append(max_price)
        query += " ORDER BY free DESC, context_tokens DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_changes(self, since_hours: int = 24) -> list[dict]:
        """Get recent deal changes."""
        conn = self._get_conn()
        cutoff = time.time() - (since_hours * 3600)
        rows = conn.execute(
            "SELECT * FROM deal_events WHERE created_at > ? ORDER BY created_at DESC",
            (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(cutoff)),)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Get dataset statistics."""
        conn = self._get_conn()
        return {
            "total_offers": conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0],
            "free_offers": conn.execute("SELECT COUNT(*) FROM offers WHERE free = 1").fetchone()[0],
            "providers": conn.execute("SELECT COUNT(DISTINCT provider_id) FROM offers").fetchone()[0],
        }


# Singleton
_service = None

def get_service() -> DealService:
    global _service
    if _service is None:
        _service = DealService()
    return _service
