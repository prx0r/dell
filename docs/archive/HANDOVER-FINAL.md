# LLM Deals — Final Handover

**Date:** 2026-08-17
**Git:** master @ 3199e8b
**Status:** OPERATIONAL — Architecture Overhaul Complete

---

## What We Built

### Data Pipeline
```
38 Source Adapters → Canonical SQLite → DealService → REST + MCP + Site
```

### Architecture (Post-Overhaul)
```
MODEL → ROUTE → SERVING ENDPOINT
  ↓       ↓           ↓
models  model_prices  serving_endpoints
  ↓       ↓           ↓
model_providers  quota_policies  performance_observations
```

### Numbers
- **1714 models** in ledger
- **3019 price observations** (append-only)
- **1821 provider relationships**
- **79 serving endpoints** (from OpenRouter)
- **7 quota policies** (OpenRouter, Google, Groq, Cloudflare)
- **1861 offers** from 65 providers
- **30 claims** with evidence
- **13 verification runs**
- **23 tool events** (hash chain)

### APIs
| Port | API | Endpoints |
|------|-----|-----------|
| 8803 | Canonical | 24 endpoints |

### New Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/free/plan` | POST | Plan workload using free routes |
| `/v1/providers/browse` | GET | Browse by category/country |
| `/v1/providers/{id}/deals` | GET | Provider's deals |
| `/v1/providers/{id}/discover` | GET | Discovery info |

---

## Data Model

### Core Tables

| Table | Records | Purpose |
|-------|---------|---------|
| models | 1714 | Canonical model identity |
| model_prices | 3019 | Append-only price observations |
| model_providers | 1821 | Model ↔ provider relationships |
| serving_endpoints | 79 | Actual serving routes |
| quota_policies | 7 | Conditional free quotas |
| performance_observations | 0 | Dell probes (ready) |
| offers | 1861 | Commercial propositions |
| claims | 30 | Extracted facts |
| evidence_v2 | 30 | Provenance records |
| verification_runs | 13 | Cryptographic audit trails |
| tool_events | 23 | Hash chain events |

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

## What Changed (Architecture Overhaul)

### Before
- Model author = serving provider (WRONG)
- Unknown quantization = "Full precision" (WRONG)
- Free = "price = 0" (INCOMPLETE)
- Context advertised = context effective (WRONG)

### After
- Model author ≠ serving provider (CORRECT)
- Unknown quantization = UNKNOWN (CORRECT)
- Free = price + quota + availability (COMPLETE)
- Context advertised ≠ context effective (MEASURED)

---

## Provider Intelligence

### OpenRouter (79 endpoints)
- Free models: 20
- Endpoints per model: 1-31
- Data: quantization, context, pricing, capabilities

### Quota Policies
| Provider | Free Quota | Condition |
|----------|------------|-----------|
| OpenRouter | 50 RPD | credits < $10 |
| OpenRouter | 1000 RPD | credits >= $10 |
| Google | 1500 RPD | None |
| Groq | 14400 RPD | None |
| Cloudflare | 10K neurons/day | None |

### Canonical States
- Quantization: KNOWN | UNKNOWN | VARIABLE
- Availability: AVAILABLE | DEGRADED | UNAVAILABLE | UNKNOWN
- Free: ZERO_PRICE | CREDIT_BACKED | ALLOWANCE_BACKED | PROMOTIONAL | UNKNOWN
- Quota: KNOWN_STATIC | KNOWN_CONDITIONAL | ACCOUNT_DEPENDENT | MEASURED | UNKNOWN

---

## Hermes Operations

### Discovery Pipeline
```
1. library-discovery → find new deals
2. library-investigate → deep-dive into deals
3. library-validate → verify deals still active
4. Canonical DB → store with full evidence
```

### Gap Analysis
```bash
python3 -m app.gap_report
# Identifies UNKNOWN/STALE fields per endpoint
# Prioritizes by: user_value × quality × unknownness
```

### Free Capacity Planning
```bash
curl -X POST http://localhost:8803/v1/free/plan \
  -H "Content-Type: application/json" \
  -d '{"task":"coding","requests":100,"min_context":64000}'
```

---

## Open Threads

| Thread | Priority | Status |
|--------|----------|--------|
| Dell canaries (probes) | HIGH | Schema ready, need implementation |
| Cloudflare adapter | HIGH | Need to fetch pricing + limits |
| Groq adapter | HIGH | Need to fetch rate limits |
| HuggingFace credits | MEDIUM | Model as recurring credit |
| Gemini account-dependent | MEDIUM | Model project-specific quota |
| Nightly gap closure | MEDIUM | Hermes investigates UNKNOWNs |
| /v1/free/plan refinement | LOW | Add fallback routing |

---

## Proof Kernel

14/14 gates pass:
- PK-01: Claims link to valid offers
- PK-02: Verification level from actual checks
- PK-03: Hash chain includes parent
- PK-04: Run root binds all Merkle roots
- PK-05: Sealed runs immutable
- PK-06: Evidence created with claims
- PK-07: Artifacts connected
- PK-08: Claims linked to correct observations
- PK-09: Semantic extraction correct
- PK-10: Events wired to offers
- PK-11: API uses verification engine
- PK-12: No price_known usage
- PK-13: Investigation terminates
- PK-14: Activation recipes exist

---

## Key Files

### Core
- `app/canonical_db.py` — SQLite kernel
- `app/api_canonical.py` — REST API
- `app/verification.py` — Proof kernel
- `app/scoring.py` — 10D scoring
- `app/gap_report.py` — Nightly analysis

### Schema
- `app/schema_canonical.sql` — Core tables
- `app/schema_ledger.sql` — Model ledger
- `app/offer_id.py` — Canonical ID constructor

### Data
- `data/provider_catalog.json` — 71 providers
- `data/PEER-REVIEW-V2.md` — Architecture review
- `data/TRUST-MODEL.md` — What "verified" means
- `data/PROVIDER-CATALOG.md` — Provider categories
