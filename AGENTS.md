# LLM Deals — Agent Operating Manual

## Mission

> LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.

## Quick Start

```bash
cd /root/ass-rape-spunk-porn
python3 -m app.cron_poll --all                    # Poll all 38 sources
python3 -m uvicorn app.api_canonical:app --port 8803  # Start API
python3 -m app.invariant_tests                     # Run proof kernel
python3 -m app.gap_report                          # Run gap analysis
```

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │            CANONICAL SQLite              │
                    │                                         │
                    │  models ← model_prices ← serving_endpoints
                    │     ↓         ↓              ↓
                    │  model_providers  quota_policies    performance_observations
                    │     ↓
                    │  offers ← claims ← evidence_v2 ← verification_runs
                    │     ↓
                    │  model_events (append-only)
                    └─────────────────────────────────────────┘
                              ↓                    ↓
                         REST API              MCP Tools
                         (port 8803)           (9 tools)
```

## Data Model

### Core Tables

| Table | Records | Purpose |
|-------|---------|---------|
| **models** | 1714 | Canonical model identity |
| **model_prices** | 3019 | Append-only price observations |
| **model_providers** | 1821 | Model ↔ provider relationships |
| **serving_endpoints** | 79 | Actual serving routes (quantization, latency, throughput) |
| **quota_policies** | 7 | Conditional free quotas |
| **performance_observations** | 0 | Dell probe history |
| **offers** | 1861 | Commercial propositions |
| **claims** | 30 | Extracted facts with evidence |
| **evidence_v2** | 30 | Provenance records |
| **verification_runs** | 13 | Cryptographic audit trails |
| **tool_events** | 23 | Hash chain events |

### Key Relationships

```
MODEL (deepseek/deepseek-r1)
  └── ROUTE (openrouter:free)
       └── SERVING ENDPOINT (Novita, fp8, 64K ctx)
            ├── quantization: fp8
            ├── latency: p50=120ms, p90=340ms
            ├── throughput: p50=45 tps
            ├── uptime: 99.2%
            ├── price: $0 (free)
            ├── quota: 50 RPD (or 1000 if $10+ credits)
            └── capabilities: tools, json_schema, streaming
```

---

## API Endpoints

### Core Data

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/models` | GET | List all models |
| `/v1/deals` | GET | List all deals |
| `/v1/deals/free` | GET | Free models ranked by utility |
| `/v1/deals/live` | GET | Verified live deals |
| `/v1/deals/hot` | GET | Unusual opportunities |
| `/v1/mega-deals` | GET | Institutional-quality deals |
| `/v1/recommend` | GET | Task-first recommendations |
| `/v1/cheapest` | GET | Cheapest for workload |

### Provider Intelligence

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/providers` | GET | List all providers |
| `/v1/providers/browse` | GET | Browse by category/country |
| `/v1/providers/{id}/deals` | GET | Provider's deals |
| `/v1/providers/{id}/discover` | GET | Discovery info |

### Free Capacity Planning

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/free/plan` | POST | Plan workload using free routes |
| `/v1/free` | GET | All free offers |

### Verification

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/verification-runs` | GET | Audit trails |
| `/v1/deals/{id}/evidence` | GET | Deal evidence |
| `/v1/deals/{id}/verification` | GET | Verification status |

### System

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/v1/stats` | GET | Dataset stats |
| `/v1/glossary` | GET | Term definitions |

---

## Hermes Operations

### Discovery Pipeline

```
1. library-discovery skill searches for new deals
   ↓
2. library-investigate skill deep-dives into deals
   ↓
3. library-validate skill verifies deals still active
   ↓
4. Canonical DB stores with full evidence
```

### How to Investigate a Provider

```bash
# 1. Check what we know
curl http://localhost:8803/v1/providers/xiaomi/discover

# 2. Browse their deals
curl http://localhost:8803/v1/providers/xiaomi/deals

# 3. Check serving endpoints
curl http://localhost:8803/v1/providers/browse?category=inference&country=China
```

### How to Plan Free Workloads

```bash
# Plan a coding workload
curl -X POST http://localhost:8803/v1/free/plan \
  -H "Content-Type: application/json" \
  -d '{
    "task": "coding",
    "requests": 100,
    "avg_input_tokens": 2000,
    "avg_output_tokens": 1000,
    "requires_tools": true,
    "min_context": 64000
  }'
```

### How to Run Gap Analysis

```bash
# See what's unknown
python3 -m app.gap_report

# Output:
# FREE INTELLIGENCE GAP REPORT
# Total free endpoints: 87
# Fully characterized: 0 (0.0%)
# GAPS:
#   missing_performance: 87
#   missing_quota: 5
```

### Cron Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| OpenRouter models | 30 min | `python3 -m app.cron_poll --source openrouter` |
| OpenRouter endpoints | 10 min | `python3 -m app.cron_poll --endpoints` |
| Cloudflare limits | 6 h | `python3 -m app.cron_poll --source cloudflare` |
| Groq limits | 6 h | `python3 -m app.cron_poll --source groq` |
| Dell canaries | 15 min | `python3 -m app.probes --free` |
| Gap report | Daily | `python3 -m app.gap_report` |

---

## Source Hierarchy

### Tier A — Official Machine API
- Model catalog
- Endpoint API
- Account headers
- Usage API

### Tier B — Official Structured Docs
- Pricing table
- Limits table
- Changelog

### Tier C — Authenticated Account Observation
- Quota response
- Rate-limit headers
- Billing state

### Tier D — Dell Synthetic Probe
- TTFT
- Throughput
- Errors
- Context acceptance
- Structured output

### Tier E — Browser Inspection
- Official public pages

### Tier F — Blogs / Reddit / Discord
- Discovery only
- Never canonical truth until confirmed

---

## Canonical States

### Quantization
- `KNOWN` — verified (fp16, fp8, int4, etc.)
- `UNKNOWN` — not yet measured
- `VARIABLE` — differs by endpoint

### Availability
- `AVAILABLE` — operational
- `DEGRADED` — reduced performance
- `UNAVAILABLE` — down
- `UNKNOWN` — not checked

### Free Mechanism
- `ZERO_PRICE` — $0 per token
- `CREDIT_BACKED` — free credits (e.g., DeepSeek ¥10)
- `ALLOWANCE_BACKED` — daily/monthly allowance (e.g., Google 1500 RPD)
- `PROMOTIONAL` — limited time
- `SUBSCRIPTION_INCLUDED` — part of paid plan
- `UNKNOWN` — mechanism unclear

### Quota State
- `KNOWN_STATIC` — fixed limit (e.g., Google 1500 RPD)
- `KNOWN_CONDITIONAL` — depends on account (e.g., OpenRouter 50/1000 RPD)
- `ACCOUNT_DEPENDENT` — varies by user
- `MEASURED` — from actual probes
- `UNKNOWN` — not measured

---

## Rules

1. **Model author ≠ serving provider** — `deepseek/deepseek-*` through OpenRouter is served by OpenRouter
2. **Unknown = UNKNOWN** — never infer "Full precision" from NULL
3. **Free = price + quota + availability** — not just "price = 0"
4. **Context advertised ≠ context effective** — measure before claiming
5. **Performance needs history** — store p50/p90 over time, not single number
6. **Every fact has provenance** — source, authority, confidence, timestamp
7. **Unknown remains unknown** — never coerce to certainty
8. **Historical is append-only** — never delete, always append
9. **Evidence is mandatory** — every deal links to source evidence
10. **Gap report drives investigation** — only investigate UNKNOWN or STALE fields

---

## Key Files

### Core Pipeline
- `app/canonical_db.py` — SQLite kernel
- `app/api_canonical.py` — REST API
- `app/verification.py` — Proof kernel
- `app/scoring.py` — 10D scoring

### New Architecture
- `app/gap_report.py` — Nightly gap analysis
- `app/schema_ledger.sql` — Model ledger schema
- `app/offer_id.py` — Canonical ID constructor

### Data
- `data/provider_catalog.json` — 71 providers
- `data/provider_discovery_pipeline.json` — OpenCode Go mapping
- `data/PEER-REVIEW-V2.md` — Architecture review
- `data/TRUST-MODEL.md` — What "verified" means
