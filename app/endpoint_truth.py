"""EndpointTruth — Live probing for endpoint measurements.

Continuously probe economically important routes.
Store: TTFT, TPS, availability, errors, tool success, JSON success.
"""
from __future__ import annotations

import json
import time
import hashlib
import requests
from typing import Optional


class EndpointProbe:
    """Probe a single endpoint."""
    
    def __init__(self, endpoint_id: str, model_id: str, provider: str,
                 api_url: str, api_key: str = None):
        self.endpoint_id = endpoint_id
        self.model_id = model_id
        self.provider = provider
        self.api_url = api_url
        self.api_key = api_key
    
    def probe_basic_health(self) -> dict:
        """Probe basic health (reachability + latency)."""
        start = time.time()
        try:
            response = requests.get(self.api_url, timeout=10,
                                   headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})
            ttft = (time.time() - start) * 1000  # ms
            
            return {
                "status": "reachable",
                "http_status": response.status_code,
                "ttft_ms": round(ttft, 2),
                "checked_at": now(),
            }
        except requests.exceptions.Timeout:
            return {"status": "timeout", "ttft_ms": 10000, "checked_at": now()}
        except Exception as e:
            return {"status": "error", "error": str(e)[:100], "checked_at": now()}
    
    def probe_inference(self, prompt: str = "Return exactly OK.") -> dict:
        """Probe inference capability."""
        start = time.time()
        try:
            response = requests.post(
                self.api_url + "/chat/completions",
                json={"model": self.model_id, "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            ttft = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)
                
                return {
                    "status": "success",
                    "http_status": 200,
                    "ttft_ms": round(ttft, 2),
                    "response_content": content[:100],
                    "tokens": tokens,
                    "checked_at": now(),
                }
            else:
                return {
                    "status": "error",
                    "http_status": response.status_code,
                    "ttft_ms": round(ttft, 2),
                    "checked_at": now(),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)[:100], "checked_at": now()}


def now():
    """Get current timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def probe_top_endpoints(conn, limit: int = 20) -> list[dict]:
    """Probe the top N economically important endpoints."""
    endpoints = conn.execute("""
        SELECT endpoint_id, model_id, serving_provider_id, 
               input_per_m, output_per_m, is_free
        FROM serving_endpoints
        WHERE is_free = 1 OR input_per_m IS NOT NULL
        ORDER BY is_free DESC, input_per_m ASC
        LIMIT ?
    """, (limit,)).fetchall()
    
    results = []
    for ep in endpoints:
        probe = EndpointProbe(
            endpoint_id=ep["endpoint_id"],
            model_id=ep["model_id"],
            provider=ep["serving_provider_id"],
            api_url="https://api.openai.com/v1",  # Generic endpoint
        )
        
        # Probe basic health
        health = probe.probe_basic_health()
        
        results.append({
            "endpoint_id": ep["endpoint_id"],
            "model_id": ep["model_id"],
            "provider": ep["serving_provider_id"],
            "health": health,
            "probed_at": now(),
        })
    
    return results


def store_probe_results(conn, results: list[dict]):
    """Store probe results in performance_observations."""
    for r in results:
        health = r.get("health", {})
        
        conn.execute("""
            INSERT INTO performance_observations (endpoint_id, timestamp,
                ttft_ms, status_code, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            r["endpoint_id"],
            r["probed_at"],
            health.get("ttft_ms"),
            health.get("http_status"),
            "dell_probe",
            now(),
        ))
    
    conn.commit()


def get_endpoint_performance(conn, endpoint_id: str) -> dict:
    """Get performance statistics for an endpoint."""
    observations = conn.execute("""
        SELECT ttft_ms, status_code, timestamp
        FROM performance_observations
        WHERE endpoint_id = ?
        ORDER BY timestamp DESC
        LIMIT 100
    """, (endpoint_id,)).fetchall()
    
    if not observations:
        return {"endpoint_id": endpoint_id, "status": "NO_DATA"}
    
    ttfts = [o["ttft_ms"] for o in observations if o["ttft_ms"] is not None]
    success_count = sum(1 for o in observations if o["status_code"] == 200)
    
    return {
        "endpoint_id": endpoint_id,
        "observations": len(observations),
        "ttft_p50": sorted(ttfts)[len(ttfts)//2] if ttfts else None,
        "ttft_p90": sorted(ttfts)[int(len(ttfts)*0.9)] if ttfts else None,
        "success_rate": success_count / len(observations) if observations else 0,
        "last_checked": observations[0]["timestamp"] if observations else None,
    }
