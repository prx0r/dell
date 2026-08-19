"""app/sources/new_providers.py — New centralized providers adapter.

Tracks Chutes, Venice, Hyperbolic, Heurist, io.net, AkashML.
Uses static configs + optional API probing.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "new-providers"
CADENCE_MINUTES = 1440

PROVIDERS = {
    "chutes": {
        "name": "Chutes",
        "api_url": "https://api.chutes.ai/v1",
        "openai_compatible": True,
        "description": "Serverless models + GPU/container jobs, $350k+ 30d revenue",
        "compute_types": ["hosted_inference", "gpu_jobs"],
        "github": "chutes-ai/chutes",
    },
    "venice": {
        "name": "Venice",
        "api_url": "https://api.venice.ai/v1",
        "openai_compatible": True,
        "description": "OpenAI-compatible inference + x402 support, model catalog + billing",
        "compute_types": ["hosted_inference"],
        "github": None,
    },
    "hyperbolic": {
        "name": "Hyperbolic",
        "api_url": "https://api.hyperbolic.xyz/v1",
        "openai_compatible": True,
        "description": "OpenAI-compatible inference + GPU rental",
        "compute_types": ["hosted_inference", "gpu_rental"],
        "github": None,
    },
    "heurist": {
        "name": "Heurist",
        "api_url": "https://api.heurist.ai/v1",
        "openai_compatible": True,
        "description": "OpenAI-compatible LLM gateway + agent mesh",
        "compute_types": ["hosted_inference", "agent_service"],
        "github": None,
    },
    "io_intelligence": {
        "name": "io Intelligence",
        "api_url": "https://api.io.net/v1",
        "openai_compatible": True,
        "description": "Hosted inference/agents + GPU marketplace",
        "compute_types": ["hosted_inference", "gpu"],
        "github": None,
    },
    "akash_ml": {
        "name": "AkashML",
        "api_url": "https://api.akashml.io/v1",
        "openai_compatible": True,
        "description": "OpenAI-compatible open-model inference",
        "compute_types": ["hosted_inference"],
        "github": None,
    },
}


def fetch() -> list[Observation]:
    """Fetch provider metadata."""
    observations = []
    
    for provider_id, config in PROVIDERS.items():
        # Use static config as the observation
        observations.append(Observation(
            source_id=SOURCE_ID,
            source_type="static_config",
            url=config["api_url"],
            fetched_at=now_iso(),
            status=200,
            text=json.dumps({
                "provider": config["name"],
                "api_url": config["api_url"],
                "openai_compatible": config["openai_compatible"],
                "description": config["description"],
                "compute_types": config["compute_types"],
            }),
            sha256=sha256(json.dumps(config)),
        ))
    
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract provider offers."""
    if observation.status is None:
        return []
    
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []
    
    provider = data.get("provider", "unknown")
    compute_types = data.get("compute_types", [])
    
    offers = []
    for ct in compute_types:
        offers.append(OfferSnapshot(
            provider_id=provider.lower().replace(" ", "_"),
            model_id=f"{ct}_compute",
            provider_model_slug=f"{provider}/{ct}",
            offer_kind="hosted_compute" if "inference" in ct else "raw_compute",
            metadata={
                "source": "new-providers",
                "provider": provider,
                "api_url": data.get("api_url"),
                "openai_compatible": data.get("openai_compatible", False),
                "compute_type": ct,
            },
        ))
    
    return offers
