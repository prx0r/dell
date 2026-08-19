"""app/friction.py — Dell's friction scoring system.

Derives friction_score from structured requirements, not arbitrary numbers.

0.0 = agent can deploy with zero manual steps
1.0 = requires extensive manual setup

Factors:
- account_required
- prepaid_credit_required
- wallet_required
- manual_approval
- docker_required
- custom_image_required
- ssh_required
- persistent_storage_setup
- network_setup
- minimum_gpu_count
- minimum_commitment
- cold_start
- API_provisionable
- agent_can_complete_setup
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FrictionFactors:
    """Structured requirements that determine friction."""
    account_required: bool = True
    prepaid_credit_required: bool = False
    wallet_required: bool = False
    manual_approval: bool = False
    docker_required: bool = False
    custom_image_required: bool = False
    ssh_required: bool = False
    persistent_storage_setup: bool = False
    network_setup: bool = False
    minimum_gpu_count: int = 1
    minimum_commitment_hours: int = 0
    cold_start_seconds: int = 0
    api_provisionable: bool = False
    agent_can_complete_setup: bool = False


# Weights for each factor (sum to 1.0)
WEIGHTS = {
    "account_required": 0.10,
    "prepaid_credit_required": 0.12,
    "wallet_required": 0.08,
    "manual_approval": 0.15,
    "docker_required": 0.08,
    "custom_image_required": 0.10,
    "ssh_required": 0.12,
    "persistent_storage_setup": 0.08,
    "network_setup": 0.05,
    "minimum_commitment": 0.10,
    "cold_start": 0.05,
}


def calculate_friction(factors: FrictionFactors) -> float:
    """Calculate friction score 0.0 (easy) to 1.0 (hard)."""
    score = 0.0

    # Boolean factors
    if factors.account_required:
        score += WEIGHTS["account_required"]
    if factors.prepaid_credit_required:
        score += WEIGHTS["prepaid_credit_required"]
    if factors.wallet_required:
        score += WEIGHTS["wallet_required"]
    if factors.manual_approval:
        score += WEIGHTS["manual_approval"]
    if factors.docker_required:
        score += WEIGHTS["docker_required"]
    if factors.custom_image_required:
        score += WEIGHTS["custom_image_required"]
    if factors.ssh_required:
        score += WEIGHTS["ssh_required"]
    if factors.persistent_storage_setup:
        score += WEIGHTS["persistent_storage_setup"]
    if factors.network_setup:
        score += WEIGHTS["network_setup"]

    # Numeric factors
    if factors.minimum_commitment_hours > 0:
        score += WEIGHTS["minimum_commitment"]

    if factors.cold_start_seconds > 60:
        score += WEIGHTS["cold_start"]

    # Agent-friendly bonus
    if factors.agent_can_complete_setup:
        score = max(0.0, score - 0.3)

    return min(1.0, score)


# Pre-configured friction profiles
FRICTION_PROFILES = {
    "modal": FrictionFactors(
        account_required=True, prepaid_credit_required=False,
        manual_approval=False, docker_required=False,
        api_provisionable=True, agent_can_complete_setup=True,
        cold_start_seconds=5,
    ),
    "runpod_serverless": FrictionFactors(
        account_required=True, prepaid_credit_required=False,
        manual_approval=False, docker_required=False,
        api_provisionable=True, agent_can_complete_setup=True,
        cold_start_seconds=10,
    ),
    "lambda": FrictionFactors(
        account_required=True, prepaid_credit_required=True,
        manual_approval=False, docker_required=False,
        api_provisionable=True, agent_can_complete_setup=True,
        cold_start_seconds=30,
    ),
    "shadeform": FrictionFactors(
        account_required=True, prepaid_credit_required=False,
        manual_approval=False, docker_required=False,
        api_provisionable=True, agent_can_complete_setup=True,
        cold_start_seconds=60,
    ),
    "vast": FrictionFactors(
        account_required=True, prepaid_credit_required=True,
        manual_approval=False, ssh_required=True,
        persistent_storage_setup=True, api_provisionable=False,
        cold_start_seconds=120,
    ),
    "salad": FrictionFactors(
        account_required=True, prepaid_credit_required=True,
        manual_approval=False, docker_required=True,
        custom_image_required=True, ssh_required=False,
        persistent_storage_setup=False, api_provisionable=False,
        agent_can_complete_setup=False, cold_start_seconds=300,
    ),
    "akash": FrictionFactors(
        account_required=True, wallet_required=True,
        manual_approval=False, docker_required=True,
        api_provisionable=True, agent_can_complete_setup=True,
        cold_start_seconds=60,
    ),
    "bittensor": FrictionFactors(
        account_required=True, wallet_required=True,
        manual_approval=False, docker_required=True,
        api_provisionable=False, agent_can_complete_setup=False,
        cold_start_seconds=120,
    ),
}


def get_friction_score(provider: str) -> float:
    """Get friction score for a provider."""
    factors = FRICTION_PROFILES.get(provider, FrictionFactors())
    return calculate_friction(factors)
