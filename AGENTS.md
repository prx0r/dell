# Dell — Agent Operating Manual

**Version:** 1.0.0
**Git SHA:** 65ddbd6
**Schema:** 7
**Status:** Production-ready

---

## Mission

> Dell provides trustworthy, machine-readable inference-economics data for LLM routing, cost optimization, and agent decision-making.

## Quick Start

```bash
cd /root/ass-rape-spunk-porn

# Run migrations
python3 -m app.migrate

# Start API
python3 -m uvicorn app.api_canonical:app --port 8803

# Run tests
python3 -m app.invariant_tests      # 14/14 proof kernel
python3 -m app.mutation_tests        # 9/10 mutation (90%)
python3 -m app.certify_final         # Final certificate
```

---

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
                    │  offer_assertions ← verification_dimensions
                    │     ↓
                    │  model_events (append-only)
                    └─────────────────────────────────────────┘
                              ↓                    ↓
                         REST API              MCP Tools
                         (port 8803)           (9 tools)
```

---

## API Reference

### Start API
```bash
python3 -m uvicorn app.api_canonical:app --port 8803
```

### Primary Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/resolve` | POST | **Primary decision primitive** |
| `/v1/routes` | GET | Search routes |
| `/v1/models` | GET | List models |
| `/v1/providers` | GET | List providers |
| `/v1/deals` | GET | List deals |
| `/v1/changes` | GET | Deal history |
| `/v1/evidence/{id}` | GET | Deal evidence |
| `/v1/coverage` | GET | Field coverage |

### Convenience Presets

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/free` | GET | Free models |
| `/v1/workhorses` | GET | Workhorse models |
| `/v1/high-value` | GET | High value models |

---

## MCP Tools (9 tools)

| Tool | Purpose |
|------|---------|
| `resolve_inference` | Primary decision tool |
| `search_routes` | Search for routes |
| `compare_routes` | Compare routes |
| `explain_route` | Explain a route |
| `get_deal_changes` | Get deal history |
| `get_provider_setup` | Get setup instructions |
| `get_dataset_stats` | Get statistics |
| `plan_free_workload` | Plan free workload |
| `list_models` | List models |

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

## Tests

```bash
python3 -m app.invariant_tests      # 14/14 proof kernel
python3 -m app.mutation_tests        # 10 mutation (90% kill)
python3 -m app.external_agent_tests  # 10 agent tests
python3 -m app.certify_final         # Final certificate
```

---

## Rules

1. Every served factual value traces to ≥1 exact claim
2. Every claim traces to exact immutable observed bytes
3. No stale fact silently masquerades as current
4. Absence, unknown, stale, conflicted and false are distinct
5. No projection overwrites historical observation truth
6. "Verified" is multidimensional and claim-specific
7. Every invariant has a negative test
8. MODEL != ENDPOINT != OFFER
9. Provider != model author
10. Unknown quantization stays UNKNOWN

---

## Key Files

### Core
- `app/services/decision.py` — Canonical resolver
- `app/services/query.py` — Shared REST/MCP logic
- `app/scoring_v3.py` — Task-dependent scoring
- `app/badge_engine.py` — Semantic badges
- `app/api_canonical.py` — REST API
- `app/mcp_canonical.py` — MCP tools
- `app/freshness.py` — TTL checking
- `app/provenance.py` — Provenance chain
- `app/resolve.py` — Resolve endpoint

### Sources (42 total)
- `app/sources/registry.py` — Source registry (42 sources)
- `app/sources/free_llm_apis.py` — awesome-free-llm-apis (145 free tiers)
- `app/sources/litellm_prices.py` — litellm model prices (3040 models)
- `app/sources/mcp_registry.py` — MCP server registry (234 tools)
- `app/sources/context_engineering.py` — Context patterns
- `app/sources/opencode.py` — OpenCode Go pricing
- `app/sources/models_dev.py` — models.dev capabilities

### Schema
- `app/migrations/0001-0007` — 7 migrations
- `app/schema_check.py` — Schema verification

### Documentation
- `docs/ARCHITECTURE.md` — Architecture
- `docs/API.md` — API reference
- `docs/MCP.md` — MCP reference
- `docs/TRUST.md` — Trust model
- `docs/SCORING.md` — Scoring system
- `docs/OPERATIONS.md` — Operations
- `docs/TESTING.md` — Testing
- `MANIFEST.json` — Machine-readable manifest
