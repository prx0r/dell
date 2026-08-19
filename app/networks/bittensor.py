"""app/networks/bittensor.py — Bittensor subnet adapter.

Tracks individual subnets as separate businesses.
Key subnets: SN64 Chutes, SN53 engy, SN51 Lium, SN62 Ridges.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any


# Key subnets with real data
SUBNETS = {
    64: {
        "name": "Chutes",
        "type": "hosted_inference",
        "priority": "S",
        "description": "Serverless models + GPU/container jobs",
        "external_revenue": 350000,  # ~$350k 30d
        "payment_method": "crypto",
    },
    53: {
        "name": "engy",
        "type": "verified_inference",
        "priority": "S",
        "description": "OpenAI/Anthropic-compatible verified inference",
        "external_revenue": None,
        "payment_method": "crypto",
    },
    51: {
        "name": "Lium",
        "type": "raw_gpu",
        "priority": "A",
        "description": "Attested GPU rental",
        "external_revenue": None,
        "payment_method": "crypto",
    },
    28: {
        "name": "gm",
        "type": "inference_arbitrage",
        "priority": "A",
        "description": "Miners place API credentials in TEE, earn spread",
        "external_revenue": None,
        "payment_method": "crypto",
    },
    62: {
        "name": "Ridges",
        "type": "agent_arena",
        "priority": "A",
        "description": "Software-engineering agent competition",
        "external_revenue": None,
        "payment_method": "crypto",
    },
    60: {
        "name": "Bitsec",
        "type": "security_agent",
        "priority": "B",
        "description": "AI security agents for vulnerability detection",
        "external_revenue": None,
        "payment_method": "crypto",
    },
}


class BittensorNetwork:
    """Bittensor subnet adapter for Dell Compute Radar."""
    
    def get_subnet_info(self, subnet_id: int) -> dict[str, Any] | None:
        """Get info for a specific subnet."""
        return SUBNETS.get(subnet_id)
    
    def get_all_subnets(self) -> list[dict[str, Any]]:
        """Get all tracked subnets."""
        return [{"subnet_id": sid, **info} for sid, info in SUBNETS.items()]
    
    def get_inference_subnets(self) -> list[dict[str, Any]]:
        """Get subnets that provide inference."""
        return [
            {"subnet_id": sid, **info}
            for sid, info in SUBNETS.items()
            if info["type"] in ("hosted_inference", "verified_inference")
        ]
    
    def get_gpu_subnets(self) -> list[dict[str, Any]]:
        """Get subnets that provide GPU compute."""
        return [
            {"subnet_id": sid, **info}
            for sid, info in SUBNETS.items()
            if info["type"] in ("raw_gpu", "gpu_jobs")
        ]
    
    def get_gpu_prices(self) -> list[dict[str, Any]]:
        """Get GPU prices from Bittensor subnets."""
        prices = []
        for sid, info in SUBNETS.items():
            if info["type"] == "raw_gpu":
                prices.append({
                    "gpu": "H100",
                    "price_per_hour_usd": 0.85,  # Estimated from subnet data
                    "currency": "TAO",
                    "network": "bittensor",
                    "subnet_id": sid,
                    "subnet_name": info["name"],
                    "status": "EXPERIMENTAL",
                    "source": "bittensor_subnet",
                })
        return prices


BITTENSOR = BittensorNetwork()
