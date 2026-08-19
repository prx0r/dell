"""app/probes.py — Dell's probe system.

Actually tests endpoints to verify they work. Sends real requests
to free tier endpoints to measure reliability, latency, and capabilities.

Probes run on a schedule (e.g., every hour) and update observations.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .observations import (
    EndpointObservation, EndpointState, ObservedSpec,
    create_observation, update_observation,
)


def probe_endpoint(
    provider: str,
    model: str,
    endpoint_url: str,
    api_key: str | None = None,
    test_prompt: str = "Say hello in one word.",
    timeout: int = 10,
) -> dict[str, Any]:
    """Probe an endpoint with a real request.
    
    Returns probe results: success, latency, ttft, error.
    """
    start = time.time()
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "",
        }
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": test_prompt}],
            "max_tokens": 50,
        }).encode()

        req = urllib.request.Request(
            endpoint_url,
            data=payload,
            headers=headers,
            method="POST",
        )

        resp_start = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ttft_ms = (resp_start - start) * 1000
            body = json.loads(resp.read().decode())
            latency_ms = (time.time() - start) * 1000

            return {
                "success": True,
                "ttft_ms": ttft_ms,
                "latency_ms": latency_ms,
                "status_code": resp.status,
                "response": body,
                "error": None,
            }

    except urllib.error.HTTPError as e:
        latency_ms = (time.time() - start) * 1000
        return {
            "success": False,
            "ttft_ms": None,
            "latency_ms": latency_ms,
            "status_code": e.code,
            "response": None,
            "error": f"HTTP {e.code}: {e.reason}",
            "is_429": e.code == 429,
        }
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return {
            "success": False,
            "ttft_ms": None,
            "latency_ms": latency_ms,
            "status_code": None,
            "response": None,
            "error": str(e),
            "is_429": False,
        }


def probe_and_update(obs: EndpointObservation, endpoint_url: str, api_key: str | None = None) -> EndpointObservation:
    """Probe an endpoint and update the observation."""
    from .observations import update_observation

    result = probe_endpoint(
        provider=obs.provider,
        model=obs.model,
        endpoint_url=endpoint_url,
        api_key=api_key,
    )

    return update_observation(
        obs,
        success=result["success"],
        latency_ms=result.get("latency_ms"),
        ttft_ms=result.get("ttft_ms"),
        rate_429=result.get("is_429", False),
        error=result.get("error"),
    )


def probe_free_endpoints(
    observations: list[EndpointObservation],
    endpoints: dict[str, str],
    api_keys: dict[str, str] | None = None,
) -> list[EndpointObservation]:
    """Probe multiple free endpoints and update observations."""
    results = []
    for obs in observations:
        key = f"{obs.provider}/{obs.model}"
        endpoint_url = endpoints.get(key)
        if not endpoint_url:
            continue

        api_key = (api_keys or {}).get(obs.provider)
        updated = probe_and_update(obs, endpoint_url, api_key)
        results.append(updated)

    return results
