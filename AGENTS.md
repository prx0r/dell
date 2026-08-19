# Dell — Live Supply Oracle

**Version:** 2.0.0
**Status:** Production-ready

---

## Mission

> Dell is the verified, machine-readable control plane for finding, benchmarking and routing AI workloads across centralized and decentralized compute.

Not a router. Not an economic authority. **The reality layer** — what's actually available, what it actually costs, and can you actually use it.

---

## Architecture

```
PASSIVE INTELLIGENCE          ACTIVE VERIFICATION
blogs, pricing pages    →     completion probe
GitHub, Discord         →     latency probe
provider docs           →     tool-call probe
models.dev, litellm     →     rate-limit sampling
                             ↓
                    DELL RESOURCE STATE
                    advertised vs observed vs verified
                             ↓
                    QDW / Hermes
                    decisions based on reality
```

---

## Core Concepts

| Concept | What It Does |
|---------|-------------|
| **Offers** | Raw market intelligence — what exists and what providers claim |
| **Resolve** | Decision engine — best option for a workload |
| **Probe** | Reality check — does it actually provision and run? |
| **Friction** | How hard is it for an agent to deploy? |

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/free` | GET | Free tier models |
| `/v1/inference/cheapest` | GET | Cheapest inference |
| `/v1/gpu/cheapest` | GET | GPU pricing |
| `/v1/compute/offers` | GET | Raw market intelligence |
| `/v1/compute/resolve` | POST | Decision engine |
| `/v1/compute/probe` | POST | Reality check |
| `/v1/providers/{id}/health` | GET | Provider health |
| `/v1/networks/{id}` | GET | Network info |
| `/v1/breakeven` | POST | API vs self-hosting |

---

## Data Sources (47)

| Type | Sources |
|------|---------|
| **LLM Pricing** | litellm-prices (3039 models), awesome-free-llm-apis (604 free) |
| **New Providers** | Chutes, Venice, Hyperbolic, Heurist, io.net, AkashML |
| **Decentralized** | Akash, Bittensor, Nosana, Prime Intellect |
| **Intelligence** | models.dev, Artificial Analysis, HuggingFace Router |
| **MCP** | MCP Registry (234 tools) |
| **Context** | Context Engineering patterns |

---

## Invariants

1. NO PRICE WITHOUT SOURCE OBSERVATION
2. NO COMPUTE WITHOUT PROBE
3. Advertised ≠ Observed ≠ Verified

---

## Quick Start

```bash
# Start API
python3 -m uvicorn app.api_canonical:app --port 8803

# Query from Hermes
hermes -z "Query Dell at http://127.0.0.1:8803/v1/free"
```
