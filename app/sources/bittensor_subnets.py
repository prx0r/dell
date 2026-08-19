"""app/sources/bittensor_subnets.py — Bittensor subnet tracker.

Each subnet is a separate business. Track individually:
- subnet_id, owner/project
- emission_rank, miners, validators
- service_type, endpoint_live, pricing
- external_revenue, emission_revenue
- status: LIVE, THIN, EXPERIMENTAL, STALE, DEAD
"""
from __future__ import annotations

import json
import urllib.request
from . import Observation, OfferSnapshot, sha256, now_iso


SOURCE_ID = "bittensor-subnets"
CADENCE_MINUTES = 360  # 6 hours

# Key subnets to track
KEY_SUBNETS = {
    64: {"name": "Chutes", "type": "hosted_inference", "priority": "S"},
    53: {"name": "engy", "type": "verified_inference", "priority": "S"},
    51: {"name": "Lium", "type": "raw_gpu", "priority": "A"},
    28: {"name": "gm", "type": "inference_arbitrage", "priority": "A"},
    62: {"name": "Ridges", "type": "agent_arena", "priority": "A"},
    67: {"name": "Harnyx", "type": "research_arena", "priority": "A"},
    60: {"name": "Bitsec", "type": "security_agent", "priority": "B"},
    11: {"name": "TrajectoryRL", "type": "agent_learning", "priority": "B"},
    96: {"name": "Verathos", "type": "verified_inference", "priority": "B"},
}


def fetch() -> list[Observation]:
    """Fetch Bittensor subnet data."""
    observations = []
    
    # Try to fetch subnet directory
    try:
        url = "https://api.bittensor.com/v1/subnets"
        req = urllib.request.Request(url, headers={"User-Agent": "dell/2.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        
        for subnet in data if isinstance(data, list) else []:
            subnet_id = subnet.get("subnet_id")
            if subnet_id in KEY_SUBNETS:
                info = KEY_SUBNETS[subnet_id]
                observations.append(Observation(
                    source_id=SOURCE_ID,
                    source_type="api",
                    url=url,
                    fetched_at=now_iso(),
                    status=resp.status,
                    text=json.dumps({
                        "subnet_id": subnet_id,
                        "name": info["name"],
                        "type": info["type"],
                        "priority": info["priority"],
                        "data": subnet,
                    }),
                    sha256=sha256(json.dumps(subnet)),
                ))
    except Exception as e:
        observations.append(Observation(
            source_id=SOURCE_ID,
            source_type="api",
            url="https://api.bittensor.com/v1/subnets",
            fetched_at=now_iso(),
            status=None,
            text=f"FETCH_ERROR: {e}",
            sha256=sha256(str(e)),
        ))
    
    return observations


def extract(observation: Observation) -> list[OfferSnapshot]:
    """Extract Bittensor subnet offers."""
    if observation.status is None or observation.text.startswith("FETCH_ERROR"):
        return []
    
    try:
        data = json.loads(observation.text)
    except json.JSONDecodeError:
        return []
    
    subnet_id = data.get("subnet_id")
    name = data.get("name", "unknown")
    compute_type = data.get("type", "unknown")
    
    return [OfferSnapshot(
        provider_id=f"bittensor_sn{subnet_id}",
        model_id=f"sn{subnet_id}_{compute_type}",
        provider_model_slug=f"bittensor/{name}",
        offer_kind="decentralized_compute",
        metadata={
            "source": "bittensor-subnets",
            "subnet_id": subnet_id,
            "name": name,
            "type": compute_type,
            "priority": data.get("priority", "C"),
        },
    )]
