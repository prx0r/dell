#!/usr/bin/env python3
"""app/canary.py — the provider live-check (is a free endpoint actually alive?).

Every day, send a tiny test request to each free provider that has a reachable endpoint and record
"live since <time>" + whether it answered. This turns "the router thinks provider X is free" into
"provider X was verified live at <time> with a real response." If a provider stops answering, the
canary flags it so the router stops sending work to a dead endpoint.

Run by cron daily: `0 0 * * * cd /root/dealradar && python3 app/canary.py`.

Providers are only canary-checked if they have a reachable endpoint + key on this box. Otherwise they
are marked 'not_reachable_here' (honest, not a failure).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "canary-report.json"

# providers reachable from THIS box, with how to probe them (OpenAI-compatible chat/completions)
PROBES = {
    "cloudflare": {
        "url": f"https://api.cloudflare.com/client/v4/accounts/{os.environ.get('CLOUDFLARE_AI_ACCOUNT_ID','')}/ai/run/@cf/meta/llama-3.2-3b-instruct",
        "key_env": "CLOUDFLARE_AI_API_KEY",
        "body": {"messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
    },
    "opencode-go": {
        "url": f"{os.environ.get('OPENCODE_GO_BASE_URL','https://opencode.ai/zen/go/v1')}/chat/completions",
        "key_env": "OPENCODE_GO_API_KEY",
        "body": {"model": "qwen3.7-flash", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "body": {"model": "openai/gpt-oss-20b:free", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
    },
}


def _probe(name: str, spec: dict) -> dict:
    import urllib.request
    key = os.environ.get(spec["key_env"], "")
    if not key:
        return {"provider": name, "status": "not_reachable_here", "note": f"no {spec['key_env']} key set"}
    req = urllib.request.Request(spec["url"], data=json.dumps(spec["body"]).encode(),
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"},
                                 method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
            ok = "result" in d or "choices" in d
            return {"provider": name, "status": "live" if ok else "error_response",
                    "latency_ms": int((time.time() - t0) * 1000),
                    "live_since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    except Exception as e:
        return {"provider": name, "status": "dead", "error": str(e)[:100],
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def run() -> dict:
    results = {name: _probe(name, spec) for name, spec in PROBES.items()}
    report = {"schema": "patala.dealradar.canary.v1",
              "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "results": results,
              "summary": {"live": sum(1 for r in results.values() if r["status"] == "live"),
                          "not_reachable_here": sum(1 for r in results.values() if r["status"] == "not_reachable_here"),
                          "dead": sum(1 for r in results.values() if r["status"] == "dead")}}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


if __name__ == "__main__":
    r = run()
    for name, res in r["results"].items():
        print(f"  {name:<12} {res['status']}" + (f" ({res.get('latency_ms')}ms)" if "latency_ms" in res else ""))
    print(json.dumps(r["summary"]))
