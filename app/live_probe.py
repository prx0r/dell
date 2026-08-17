"""app/live_probe.py — Live verification of free API endpoints.

Actually tests if free endpoints work by sending minimal requests.
Records: last_live_success_at, latency, response validity.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE_LOG = ROOT / "data" / "probe-log.json"


# Known free endpoints to probe
FREE_ENDPOINTS = {
    "opencode-zen": {
        "url": "https://opencode.ai/v1/models",
        "method": "GET",
        "headers": {"User-Agent": "deal-radar/2.0"},
        "auth": False,
        "timeout": 10,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "method": "GET",
        "headers": {"User-Agent": "deal-radar/2.0"},
        "auth": False,
        "timeout": 10,
    },
    "hf-router": {
        "url": "https://router.huggingface.co/v1/models",
        "method": "GET",
        "headers": {"User-Agent": "deal-radar/2.0"},
        "auth": False,
        "timeout": 15,
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/models",
        "method": "GET",
        "headers": {"User-Agent": "deal-radar/2.0"},
        "auth": False,  # Will fail without key, but tests endpoint
        "timeout": 10,
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/models",
        "method": "GET",
        "headers": {"User-Agent": "deal-radar/2.0"},
        "auth": False,
        "timeout": 10,
    },
    "sensenova": {
        "url": "https://api.sensenova.ai/v1/models",
        "method": "GET",
        "headers": {"User-Agent": "deal-radar/2.0"},
        "auth": False,
        "timeout": 10,
    },
    "zai": {
        "url": "https://open.bigmodel.cn/api/paas/v4/models",
        "method": "GET",
        "headers": {"User-Agent": "deal-radar/2.0"},
        "auth": False,
        "timeout": 10,
    },
}


def probe_endpoint(provider_id: str, config: dict = None) -> dict:
    """Probe a single free endpoint.
    
    Returns:
        provider_id: str
        live: bool
        latency_ms: float
        status_code: int
        model_count: int (if response is model list)
        error: str or None
        probed_at: str
    """
    if config is None:
        config = FREE_ENDPOINTS.get(provider_id)
    if not config:
        return {"provider_id": provider_id, "live": False, "error": "No probe config"}

    url = config["url"]
    headers = config.get("headers", {})
    timeout = config.get("timeout", 10)

    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=timeout)
        latency = (time.time() - t0) * 1000
        text = resp.read().decode("utf-8", errors="replace")

        # Try to parse as JSON to count models
        model_count = 0
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                model_count = len(data.get("data", []))
            elif isinstance(data, list):
                model_count = len(data)
        except json.JSONDecodeError:
            pass

        return {
            "provider_id": provider_id,
            "live": True,
            "latency_ms": round(latency, 1),
            "status_code": resp.status,
            "model_count": model_count,
            "error": None,
            "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    except urllib.error.HTTPError as e:
        latency = (time.time() - t0) * 1000
        # 401/403 = endpoint exists but needs auth (still "live")
        live = e.code in (401, 403)
        return {
            "provider_id": provider_id,
            "live": live,
            "latency_ms": round(latency, 1),
            "status_code": e.code,
            "model_count": 0,
            "error": "HTTP %d (auth required)" % e.code if live else str(e),
            "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return {
            "provider_id": provider_id,
            "live": False,
            "latency_ms": round(latency, 1),
            "status_code": None,
            "model_count": 0,
            "error": str(e)[:100],
            "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def probe_all() -> dict:
    """Probe all known free endpoints."""
    results = {}
    for provider_id, config in FREE_ENDPOINTS.items():
        result = probe_endpoint(provider_id, config)
        results[provider_id] = result

    # Save probe log
    PROBE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROBE_LOG, "w") as f:
        json.dump(results, f, indent=2)

    return results


def get_probe_status(provider_id: str) -> dict | None:
    """Get last probe result for a provider."""
    if not PROBE_LOG.exists():
        return None
    data = json.loads(PROBE_LOG.read_text())
    return data.get(provider_id)


def get_all_probe_status() -> dict:
    """Get all probe results."""
    if not PROBE_LOG.exists():
        return {}
    return json.loads(PROBE_LOG.read_text())
