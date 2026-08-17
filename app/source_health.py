"""Parser health tracking and degradation detection."""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_health_state: dict[str, dict] = {}
DEGRADATION_THRESHOLD = 3
RECOVERY_THRESHOLD = 2


def record_fetch(source_id: str, success: bool, latency_ms: float, error: str = None) -> None:
    """Record a fetch attempt for a source.

    Args:
        source_id: Identifier for the data source.
        success: Whether the fetch succeeded.
        latency_ms: Fetch latency in milliseconds.
        error: Error message if the fetch failed.
    """
    now = time.time()

    if source_id not in _health_state:
        _health_state[source_id] = {
            "total_fetches": 0,
            "successes": 0,
            "failures": 0,
            "consecutive_failures": 0,
            "consecutive_successes": 0,
            "last_fetch_time": None,
            "last_success_time": None,
            "last_failure_time": None,
            "last_error": None,
            "avg_latency_ms": 0,
            "status": "unknown",
            "degraded_since": None,
        }

    state = _health_state[source_id]
    state["total_fetches"] += 1
    state["last_fetch_time"] = now

    if success:
        state["successes"] += 1
        state["consecutive_successes"] += 1
        state["consecutive_failures"] = 0
        state["last_success_time"] = now
        state["last_error"] = None

        total = state["total_fetches"]
        state["avg_latency_ms"] = (
            (state["avg_latency_ms"] * (total - 1) + latency_ms) / total
        )

        if state["status"] == "degraded":
            if state["consecutive_successes"] >= RECOVERY_THRESHOLD:
                state["status"] = "healthy"
                state["degraded_since"] = None
                logger.info("Source %s recovered after %d consecutive successes", source_id, RECOVERY_THRESHOLD)
        elif state["status"] in ("unknown", "unhealthy"):
            state["status"] = "healthy"
    else:
        state["failures"] += 1
        state["consecutive_failures"] += 1
        state["consecutive_successes"] = 0
        state["last_failure_time"] = now
        state["last_error"] = error

        if state["consecutive_failures"] >= DEGRADATION_THRESHOLD:
            if state["status"] != "degraded":
                state["status"] = "degraded"
                state["degraded_since"] = now
                logger.warning(
                    "Source %s marked DEGRADED after %d consecutive failures",
                    source_id,
                    state["consecutive_failures"],
                )
            elif state["consecutive_failures"] >= DEGRADATION_THRESHOLD * 2:
                state["status"] = "unhealthy"
                logger.error(
                    "Source %s marked UNHEALTHY after %d consecutive failures",
                    source_id,
                    state["consecutive_failures"],
                )

    logger.debug(
        "Recorded fetch for %s: success=%s, latency=%.1fms, status=%s",
        source_id,
        success,
        latency_ms,
        state["status"],
    )


def get_health() -> dict:
    """Get health status for all tracked sources.

    Returns:
        Dict mapping source_id to health state dict with fields:
            total_fetches, successes, failures, consecutive_failures,
            consecutive_successes, last_fetch_time, last_success_time,
            last_failure_time, last_error, avg_latency_ms, status,
            degraded_since
    """
    return {sid: dict(state) for sid, state in _health_state.items()}


def is_healthy(source_id: str) -> bool:
    """Check if a source is currently healthy.

    Args:
        source_id: Identifier for the data source.

    Returns:
        True if the source status is 'healthy' or 'unknown' (no data yet).
    """
    if source_id not in _health_state:
        return True
    status = _health_state[source_id].get("status", "unknown")
    return status in ("healthy", "unknown")


def get_source_status(source_id: str) -> str:
    """Get the status string for a specific source.

    Args:
        source_id: Identifier for the data source.

    Returns:
        Status string: 'healthy', 'degraded', 'unhealthy', or 'unknown'.
    """
    if source_id not in _health_state:
        return "unknown"
    return _health_state[source_id].get("status", "unknown")


def reset_source(source_id: str) -> None:
    """Reset health state for a source.

    Args:
        source_id: Identifier for the data source.
    """
    if source_id in _health_state:
        del _health_state[source_id]
        logger.info("Reset health state for source %s", source_id)
