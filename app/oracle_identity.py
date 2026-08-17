"""Identity semantics for Oracle-1.

Fundamental ontology:
  MODEL != CHECKPOINT != PROVIDER ALIAS != SERVING ENDPOINT != ROUTING ALIAS != OFFER
"""
from __future__ import annotations

import hashlib
from typing import Optional


class ModelIdentity:
    """Canonical model identity."""
    
    @staticmethod
    def create(family: str, checkpoint: str = None, variant: str = None) -> str:
        """Create canonical model identity."""
        if checkpoint:
            return f"{family}/{checkpoint}"
        return family
    
    @staticmethod
    def parse(model_id: str) -> dict:
        """Parse model identity."""
        parts = model_id.split("/")
        if len(parts) == 2:
            return {"family": parts[0], "checkpoint": parts[1]}
        return {"family": model_id, "checkpoint": None}


class EndpointIdentity:
    """Serving endpoint identity (distinct from model)."""
    
    @staticmethod
    def create(provider: str, model_id: str, quantization: str = "unknown") -> str:
        """Create endpoint identity."""
        return f"{provider}:{model_id}:{quantization}"
    
    @staticmethod
    def parse(endpoint_id: str) -> dict:
        """Parse endpoint identity."""
        parts = endpoint_id.split(":")
        if len(parts) == 3:
            return {"provider": parts[0], "model": parts[1], "quantization": parts[2]}
        return {"provider": endpoint_id, "model": None, "quantization": "unknown"}


class OfferIdentity:
    """Commercial offer identity (distinct from endpoint)."""
    
    @staticmethod
    def create(provider: str, model_id: str, offer_type: str, region: str = "global") -> str:
        """Create offer identity."""
        model_clean = model_id.lower().replace("/", ":")
        return f"{provider}:{model_clean}:{offer_type}:{region}"
    
    @staticmethod
    def parse(offer_id: str) -> dict:
        """Parse offer identity."""
        parts = offer_id.split(":")
        if len(parts) == 4:
            return {
                "provider": parts[0],
                "model": parts[1],
                "offer_type": parts[2],
                "region": parts[3],
            }
        return {"provider": offer_id, "model": None, "offer_type": None, "region": None}


def resolve_aliases(conn, model_id: str) -> list[dict]:
    """Resolve all aliases for a model."""
    aliases = []
    
    # Check model_providers for provider aliases
    rows = conn.execute("""
        SELECT provider_id, offer_type FROM model_providers
        WHERE model_id = ?
    """, (model_id,)).fetchall()
    
    for row in rows:
        aliases.append({
            "type": "provider_alias",
            "provider": row["provider_id"],
            "offer_type": row["offer_type"],
        })
    
    # Check serving_endpoints for serving aliases
    rows = conn.execute("""
        SELECT endpoint_id, serving_provider_id, quantization
        FROM serving_endpoints
        WHERE model_id = ?
    """, (model_id,)).fetchall()
    
    for row in rows:
        aliases.append({
            "type": "serving_alias",
            "endpoint": row["endpoint_id"],
            "provider": row["serving_provider_id"],
            "quantization": row["quantization"],
        })
    
    return aliases


def find_model_collisions(conn) -> list[dict]:
    """Find cases where same model name maps to different checkpoints."""
    # Group by model_id prefix
    rows = conn.execute("""
        SELECT model_id, COUNT(DISTINCT family) as families
        FROM models
        GROUP BY model_id
        HAVING families > 1
    """).fetchall()
    
    return [{"model_id": r["model_id"], "families": r["families"]} for r in rows]
