"""app/sources/decentralized_compute.py — Decentralized compute providers adapter.

Tracks Akash, Bittensor, Nosana, Prime Intellect, and other decentralized
compute platforms. These provide free/cheap GPU compute that Dell can recommend.
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "decentralized-compute"
CADENCE_MINUTES = 1440

# Platform configurations
PLATFORMS = {
    "akash": {
        "name": "Akash Network",
        "type": "marketplace",
        "api_url": "https://api.akash.network/v1",
        "description": "Decentralized serverless compute marketplace",
        "compute_types": ["gpu", "cpu", "storage"],
    },
    "bittensor": {
        "name": "Bittensor",
        "type": "inference_network",
        "api_url": "https://api.bittensor.com/v1",
        "description": "Decentralized neural network subnets",
        "compute_types": ["inference", "training"],
    },
    "nosana": {
        "name": "Nosana",
        "type": "compute_network",
        "api_url": "https://api.nosana.io/v1",
        "description": "Solana-based decentralized compute",
        "compute_types": ["gpu", "jobs"],
    },
    "prime_intellect": {
        "name": "Prime Intellect",
        "type": "gpu_cloud",
        "api_url": "https://api.primeintellect.ai/v1",
        "description": "Peer-to-peer GPU compute",
        "compute_types": ["gpu", "inference"],
    },
}


def fetch() -> list[Observation]:
    """Fetch platform metadata from GitHub repos."""
    observations = []
    
    for platform_id, config in PLATFORMS.items():
        try:
            # Try to fetch repo metadata
            repo_url = f"https://api.github.com/repos/{_get_github_repo(platform_id)}"
            req = urllib.request.Request(repo_url, headers={"User-Agent": "dell/2.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type="github_api",
                url=repo_url,
                fetched_at=now_iso(),
                status=resp.status,
                text=json.dumps({
                    "platform": config["name"],
                    "type": config["type"],
                    "stars": data.get("stargazers_count", 0),
                    "description": data.get("description", ""),
                    "api_url": config["api_url"],
                    "compute_types": config["compute_types"],
                }),
                sha256=sha256(json.dumps(data)),
            ))
        except Exception as e:
            observations.append(Observation(
                source_id=SOURCE_ID,
                source_type="github_api",
                url=f"https://api.github.com/repos/{_get_github_repo(platform_id)}",
                fetched_at=now_iso(),
                status=None,
                text=f"FETCH_ERROR: {e}",
                sha256=sha256(str(e)),
            ))
    
    return observations


def _get_github_repo(platform_id: str) -> str:
    """Map platform ID to GitHub repo."""
    repos = {
        "akash": "akash-network/node",
        "bittensor": "RaoFoundation/bittensor",
        "nosana": "nosana-ci/nosana-kit",
        "prime_intellect": "PrimeIntellect-ai/prime",
    }
    return repos.get(platform_id, platform_id)


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract platform offers from observations."""
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []
    
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []
    
    platform = data.get("platform", "unknown")
    compute_types = data.get("compute_types", [])
    
    offers = []
    for compute_type in compute_types:
        offers.append(OfferSnapshot(
            provider_id=platform.lower().replace(" ", "_"),
            model_id=f"{compute_type}_compute",
            provider_model_slug=f"{platform}/{compute_type}",
            offer_kind="decentralized_compute",
            metadata={
                "source": "decentralized-compute",
                "platform": platform,
                "type": data.get("type"),
                "stars": data.get("stars", 0),
                "compute_type": compute_type,
                "api_url": data.get("api_url"),
            },
        ))
    
    return offers
