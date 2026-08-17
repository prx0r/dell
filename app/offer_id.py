"""Canonical identity for offers — single source of truth for ID generation.

No module is allowed to hand-build IDs with string formatting.
All IDs must go through OfferId.create().
"""
from __future__ import annotations

import hashlib


class OfferId:
    """Canonical offer identity constructor.
    
    Format: provider:model_clean:offer_type:region
    """
    
    @staticmethod
    def create(provider_id: str, model_id: str, offer_type: str,
               region: str = "global") -> str:
        """Generate stable offer_id.
        
        This is the ONLY way to create offer IDs in the system.
        No string formatting allowed elsewhere.
        """
        if not provider_id:
            raise ValueError("provider_id is required")
        if not model_id:
            raise ValueError("model_id is required")
        if not offer_type:
            raise ValueError("offer_type is required")
        
        model_clean = (model_id or "").lower().replace("/", ":")
        region_clean = (region or "global").lower()
        
        return f"{provider_id}:{model_clean}:{offer_type}:{region_clean}"
    
    @staticmethod
    def parse(offer_id: str) -> dict:
        """Parse an offer_id back into components."""
        parts = offer_id.split(":")
        if len(parts) == 4:
            return {
                "provider_id": parts[0],
                "model_id": parts[1],
                "offer_type": parts[2],
                "region": parts[3],
            }
        elif len(parts) == 5:
            # Handle case where model_id contains a colon
            return {
                "provider_id": parts[0],
                "model_id": parts[1] + ":" + parts[2],
                "offer_type": parts[3],
                "region": parts[4],
            }
        else:
            raise ValueError(f"Invalid offer_id format: {offer_id}")
    
    @staticmethod
    def validate(offer_id: str) -> bool:
        """Validate an offer_id format."""
        try:
            OfferId.parse(offer_id)
            return True
        except ValueError:
            return False


def generate_offer_id(provider_id: str, model_id: str, offer_type: str,
                      region: str = "global") -> str:
    """Legacy wrapper — use OfferId.create() instead."""
    return OfferId.create(provider_id, model_id, offer_type, region)
