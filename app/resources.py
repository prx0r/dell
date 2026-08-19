"""app/resources.py — Dell's resource model.

Model resources, not just LLM providers:

network → market/subnet → service → resource → quote → live observation → verified capability

This lets Dell represent:
- Chutes (serverless models + GPU jobs)
- Bittensor subnets (each is a separate business)
- Akash (raw compute + hosted inference)
- Venice (OpenAI-compatible inference + x402)
- Hyperbolic (inference + GPU rental)
- Heurist (LLM gateway + agent mesh)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComputeType(Enum):
    HOSTED_INFERENCE = "hosted_inference"
    RAW_GPU = "raw_gpu"
    CONTAINER_JOBS = "container_jobs"
    AGENT_SERVICE = "agent_service"
    SECURITY_AGENT = "security_agent"
    TRAINING = "training"
    STORAGE = "storage"


class ResourceType(Enum):
    MODEL = "model"
    GPU = "gpu"
    AGENT = "agent"
    SERVICE = "service"
    CONTAINER = "container"


class QuoteStatus(Enum):
    LIVE = "LIVE"
    THIN = "THIN"
    EXPERIMENTAL = "EXPERIMENTAL"
    STALE = "STALE"
    DEAD = "DEAD"


@dataclass
class ResourceQuote:
    """A specific quote for compute."""
    resource_id: str
    network: str
    market: str | None = None
    service: str | None = None
    resource_type: ResourceType = ResourceType.MODEL
    compute_type: ComputeType = ComputeType.HOSTED_INFERENCE
    
    # Pricing
    price_per_hour: float | None = None
    price_per_token: float | None = None
    price_per_gpu_hour: float | None = None
    
    # Capabilities
    gpu_type: str | None = None  # H100, A100, etc.
    gpu_count: int | None = None
    context_window: int | None = None
    supports_inference: bool = True
    supports_training: bool = False
    supports_container: bool = False
    
    # Verification
    last_probe_at: str | None = None
    probe_success: bool = False
    observed_latency_ms: float | None = None
    observed_quality: float | None = None
    observed_capacity: str | None = None
    
    # Economic viability
    emission_rank: int | None = None  # Bittensor specific
    external_revenue: float | None = None
    emission_revenue: float | None = None
    payment_method: str = "crypto"
    
    # Status
    status: QuoteStatus = QuoteStatus.UNKNOWN
    confidence: float = 0.0


@dataclass
class NetworkState:
    """State of a compute network."""
    network_id: str
    name: str
    type: str  # "centralized", "decentralized", "hybrid"
    total_resources: int = 0
    active_resources: int = 0
    health_score: float = 0.0
    last_updated: str = ""
    
    # Economic
    total_revenue_30d: float | None = None
    active_users: int | None = None
    growth_rate: float | None = None


@dataclass
class ServiceState:
    """State of a service within a network."""
    service_id: str
    network_id: str
    name: str
    compute_type: ComputeType
    
    # Infrastructure
    endpoint_url: str | None = None
    openai_compatible: bool = False
    
    # Performance
    median_ttft_ms: float | None = None
    median_latency_ms: float | None = None
    success_rate: float = 0.0
    total_probes: int = 0
    
    # Status
    status: QuoteStatus = QuoteStatus.UNKNOWN
    confidence: float = 0.0


def classify_resource(
    network: str,
    compute_type: str,
    has_api: bool = False,
    has_gpu: bool = False,
) -> tuple[str, ComputeType]:
    """Classify a resource into network/market/service hierarchy."""
    if network == "bittensor":
        if compute_type in ("inference", "mining"):
            return "bittensor", ComputeType.HOSTED_INFERENCE
        elif compute_type == "gpu":
            return "bittensor", ComputeType.RAW_GPU
        else:
            return "bittensor", ComputeType.AGENT_SERVICE
    elif network == "akash":
        if has_api:
            return "akash", ComputeType.HOSTED_INFERENCE
        else:
            return "akash", ComputeType.RAW_GPU
    else:
        return network, ComputeType.HOSTED_INFERENCE
