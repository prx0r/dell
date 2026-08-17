"""Standard workload profiles for deal evaluation."""

import logging

logger = logging.getLogger(__name__)

WORKLOADS = {
    "coding_agent": {
        "name": "coding_agent",
        "description": "Autonomous coding agent with tool use, iterates on code",
        "tokens_per_job": 15000,
        "jobs_per_day": 50,
        "cache_hit_rate": 0.15,
        "quality_floor": 0.85,
        "avg_input_tokens": 8000,
        "avg_output_tokens": 7000,
        "peak_rpm": 20,
    },
    "batch_extraction": {
        "name": "batch_extraction",
        "description": "Bulk data extraction and transformation jobs",
        "tokens_per_job": 5000,
        "jobs_per_day": 500,
        "cache_hit_rate": 0.3,
        "quality_floor": 0.7,
        "avg_input_tokens": 3000,
        "avg_output_tokens": 2000,
        "peak_rpm": 100,
    },
    "interactive_chat": {
        "name": "interactive_chat",
        "description": "Real-time conversational assistant with low latency",
        "tokens_per_job": 2000,
        "jobs_per_day": 200,
        "cache_hit_rate": 0.1,
        "quality_floor": 0.8,
        "avg_input_tokens": 1200,
        "avg_output_tokens": 800,
        "peak_rpm": 60,
    },
    "long_context": {
        "name": "long_context",
        "description": "Large document analysis requiring extensive context windows",
        "tokens_per_job": 50000,
        "jobs_per_day": 20,
        "cache_hit_rate": 0.05,
        "quality_floor": 0.9,
        "avg_input_tokens": 40000,
        "avg_output_tokens": 10000,
        "peak_rpm": 5,
    },
    "translation": {
        "name": "translation",
        "description": "High-volume translation tasks with predictable patterns",
        "tokens_per_job": 3000,
        "jobs_per_day": 300,
        "cache_hit_rate": 0.4,
        "quality_floor": 0.75,
        "avg_input_tokens": 1500,
        "avg_output_tokens": 1500,
        "peak_rpm": 80,
    },
    "research": {
        "name": "research",
        "description": "Deep research and analysis requiring high quality outputs",
        "tokens_per_job": 25000,
        "jobs_per_day": 30,
        "cache_hit_rate": 0.1,
        "quality_floor": 0.95,
        "avg_input_tokens": 15000,
        "avg_output_tokens": 10000,
        "peak_rpm": 10,
    },
}


def get_workload(name: str) -> dict:
    """Get a workload profile by name.

    Args:
        name: Name of the workload profile.

    Returns:
        Workload dict with keys: name, description, tokens_per_job,
        jobs_per_day, cache_hit_rate, quality_floor, avg_input_tokens,
        avg_output_tokens, peak_rpm.

    Raises:
        KeyError: If workload name is not found.
    """
    if name not in WORKLOADS:
        available = ", ".join(sorted(WORKLOADS.keys()))
        raise KeyError(f"Unknown workload '{name}'. Available: {available}")
    return WORKLOADS[name].copy()


def list_workloads() -> list[dict]:
    """List all available workload profiles.

    Returns:
        List of workload dicts.
    """
    return [w.copy() for w in WORKLOADS.values()]
