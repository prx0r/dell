# Dell — Fresh Agent Guide

**Last updated:** 2026-08-18
**Git SHA:** 4abdd25

---

## What Is Dell?

Dell is a **production-grade inference-economics oracle** for llmdeals.org. It catalogs LLM offers, tracks prices, verifies deals, and provides machine-readable provenance.

**Key fact:** Dell has 1861 offers across 65 providers, with 33% full provenance coverage.

---

## Quick Start (5 minutes)

### 1. Start the API

```bash
cd /root/ass-rape-spunk-porn
python3 -m uvicorn app.api_canonical:app --port 8803
```

### 2. Ask a question

```bash
# What's the cheapest coding model?
curl "http://localhost:8803/v1/recommend?task=coding&limit=3"

# What free models are available?
curl "http://localhost:8803/v1/deals/free?limit=5"

# Plan a free workload
curl -X POST "http://localhost:8803/v1/free/plan" \
  -H "Content-Type: application/json" \
  -d '{"task":"coding","requests":100,"min_context":64000}'
```

### 3. Check verification status

```bash
# Is this deal verified?
curl "http://localhost:8803/v1/deals/opencode-go:opencode-go:gpt-5.6-luna:usage_multiplier:global/verification"

# What evidence supports this price?
curl "http://localhost:8803/v1/deals/opencode-go:opencode-go:gpt-5.6-luna:usage_multiplier:global/evidence"
```

---

## API Reference

### Core Endpoints

| Endpoint | Method | Purpose | Example |
|----------|--------|---------|---------|
| `/health` | GET | Health check | `curl localhost:8803/health` |
| `/v1/stats` | GET | Dataset stats | `curl localhost:8803/v1/stats` |
| `/v1/models` | GET | List models | `curl localhost:8803/v1/models?limit=10` |
| `/v1/deals` | GET | List deals | `curl localhost:8803/v1/deals?limit=10` |
| `/v1/deals/free` | GET | Free models | `curl localhost:8803/v1/deals/free?limit=5` |
| `/v1/deals/live` | GET | Verified live | `curl localhost:8803/v1/deals/live` |
| `/v1/mega-deals` | GET | Mega deals | `curl localhost:8803/v1/mega-deals` |
| `/v1/recommend` | GET | Recommend | `curl localhost:8803/v1/recommend?task=coding` |
| `/v1/free/plan` | POST | Plan workload | See below |

### Provider Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/providers` | GET | List providers |
| `/v1/providers/browse` | GET | Browse by category |
| `/v1/providers/{id}/deals` | GET | Provider deals |
| `/v1/providers/{id}/discover` | GET | Discovery info |

### Verification Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/verification-runs` | GET | Audit trails |
| `/v1/deals/{id}/evidence` | GET | Deal evidence |
| `/v1/deals/{id}/verification` | GET | Verification status |

---

## MCP Tools (9 tools)

| Tool | Purpose |
|------|---------|
| `get_dataset_stats` | Get dataset statistics |
| `list_models` | List available models |
| `list_providers` | List providers |
| `get_provider_setup` | Get setup instructions |
| `find_inference_deals` | Find deals by task |
| `recommend_model` | Recommend model |
| `explain_deal` | Explain a deal |
| `get_deal_changes` | Get deal history |
| `get_dataset_stats` | Get stats |

---

## Common Tasks

### Task 1: Find cheapest coding model

```bash
curl "http://localhost:8803/v1/recommend?task=coding&limit=3"
```

Response:
```json
{
  "pick": "anthropic/claude-opus-5",
  "provider": "anthropic",
  "vector": {"coding": 96, "tool_calling": 70},
  "badges": ["free", "coder", "workhorse"]
}
```

### Task 2: Plan free workload

```bash
curl -X POST "http://localhost:8803/v1/free/plan" \
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

Response:
```json
{
  "task": "coding",
  "requests": 100,
  "recommended": [...],
  "fallback_plan": [...],
  "summary": {"can_complete_free": false}
}
```

### Task 3: Check if deal is verified

```bash
curl "http://localhost:8803/v1/deals/{offer_id}/verification"
```

Response:
```json
{
  "verification_level": "PRIMARY_EVIDENCE",
  "claims_count": 3,
  "evidence_count": 3,
  "latest_check_at": "2026-08-18T..."
}
```

### Task 4: Get evidence for a price

```bash
curl "http://localhost:8803/v1/deals/{offer_id}/evidence"
```

Response:
```json
{
  "deal_id": "opencode-go:opencode-go:gpt-5.6-luna:usage_multiplier:global",
  "evidence": [
    {
      "evidence_id": 1,
      "claim_id": 37,
      "authority": "provider_api",
      "selector": "https://dev.opencode.ai/go"
    }
  ]
}
```

### Task 5: Browse providers by country

```bash
curl "http://localhost:8803/v1/providers/browse?country=China"
```

---

## Data Model (21 tables)

| Table | Purpose |
|-------|---------|
| models | Canonical model identity |
| model_prices | Price observations |
| model_providers | Model ↔ provider |
| serving_endpoints | Actual routes |
| quota_policies | Free quotas |
| offer_assertions | Field-level claims |
| verification_dimensions | Verification predicates |
| freshness_policies | TTL rules |
| negative_observations | Absence records |
| source_authority | Authority rules |
| economic_access | Access classification |
| offers | Commercial propositions |
| claims | Extracted claims |
| evidence_v2 | Evidence records |
| verification_runs | Audit trails |
| tool_events | Hash chain |
| activation_recipes | Setup guides |
| schema_migrations | Migration tracking |

---

## Key Concepts

### Provenance Chain
```
served field → offer_assertion → claim → source_observation → source
```

### Freshness
- Different facts decay at different rates
- Prices: 24 hours
- Context: 30 days
- Model author: 1 year

### Identity
- MODEL: `deepseek/deepseek-r1`
- ENDPOINT: `openrouter:deepseek/deepseek-r1:fp8`
- OFFER: `openrouter:deepseek:deepseek-r1:free:global`

### Economic Access
- `FREE_QUOTA` — Free up to a limit
- `ZERO_MARGINAL_PRICE` — Truly free
- `TRIAL_CREDIT` — Free credits
- `CONDITIONAL_FREE` — Free with conditions

---

## Running Tests

```bash
# Proof kernel (14 tests)
python3 -m app.invariant_tests

# Mutation tests (10 tests, 90% kill rate)
python3 -m app.mutation_tests

# External agent tests (10 tests)
python3 -m app.external_agent_tests

# Red team oracle (30 tests)
python3 -m app.red_team_oracle

# Utility certification
python3 -m app.certify_utility

# Full certification
python3 -m app.certify --profile production
```

---

## Troubleshooting

### API won't start
```bash
# Check if port is in use
lsof -i :8803

# Kill existing process
kill -9 $(lsof -t -i:8803)

# Start fresh
python3 -m uvicorn app.api_canonical:app --port 8803
```

### No deals returned
```bash
# Check if offers exist
curl "http://localhost:8803/v1/stats"

# Check if offers have price_state
curl "http://localhost:8803/v1/deals?limit=5"
```

### Verification shows UNKNOWN
```bash
# Check if claims exist
curl "http://localhost:8803/v1/deals/{offer_id}/verification"

# If no claims, offer needs provenance
python3 -m app.certify_utility
```

---

## Key Files

| File | Purpose |
|------|---------|
| `app/api_canonical.py` | REST API |
| `app/mcp_server.py` | MCP tools |
| `app/freshness.py` | TTL checking |
| `app/provenance.py` | Provenance chain |
| `app/oracle_identity.py` | Identity separation |
| `app/economics.py` | Access classification |
| `app/verification.py` | Verification engine |
| `app/scoring.py` | 10D scoring |
| `app/migrate.py` | Run migrations |
| `app/schema_check.py` | Verify schema |
| `app/certify.py` | Production certification |
| `app/certify_utility.py` | Utility certification |

---

## Documentation

| Doc | Purpose |
|-----|---------|
| `AGENTS.md` | Operating manual |
| `data/HANDOVER-FINAL.md` | System map |
| `data/ORACLE-ARCHITECTURE.md` | Architecture |
| `data/DELL-ROADMAP.md` | Development roadmap |
| `data/PROVIDER-CATALOG.md` | Provider list |
| `data/TRUST-MODEL.md` | Trust model |
| `data/INVESTIGATION-PROTOCOL.md` | Discovery |
| `data/MONETIZATION.md` | Business model |
| `data/PEER-REVIEW-SYNTHESIS.md` | Review synthesis |
| `data/reports/DELL-EXTERNAL-UTILITY-AUDIT.md` | Audit report |
