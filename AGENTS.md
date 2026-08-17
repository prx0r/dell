# Dell — Agent Operating Manual

**Last updated:** 2026-08-18
**Git SHA:** 4abdd25
**Status:** Production-ready data layer

---

## Quick Start

```bash
cd /root/ass-rape-spunk-porn

# Run migrations
python3 -m app.migrate

# Start API
python3 -m uvicorn app.api_canonical:app --port 8803

# Run tests
python3 -m app.invariant_tests      # 14 proof kernel tests
python3 -m app.mutation_tests        # 10 mutation tests (90% kill)
python3 -m app.external_agent_tests  # 10 agent tests
python3 -m app.certify_utility       # Utility certification
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

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/v1/stats` | GET | Dataset stats |
| `/v1/models` | GET | List models |
| `/v1/deals` | GET | List deals |
| `/v1/deals/free` | GET | Free models |
| `/v1/deals/live` | GET | Verified live |
| `/v1/mega-deals` | GET | Mega deals |
| `/v1/recommend` | GET | Recommend |
| `/v1/free/plan` | POST | Plan workload |

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

## MCP Tools

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

---

## Common Tasks

### Find cheapest coding model
```bash
curl "http://localhost:8803/v1/recommend?task=coding&limit=3"
```

### Plan free workload
```bash
curl -X POST "http://localhost:8803/v1/free/plan" \
  -H "Content-Type: application/json" \
  -d '{"task":"coding","requests":100,"min_context":64000}'
```

### Check verification
```bash
curl "http://localhost:8803/v1/deals/{offer_id}/verification"
```

### Get evidence
```bash
curl "http://localhost:8803/v1/deals/{offer_id}/evidence"
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
python3 -m app.invariant_tests      # 14 proof kernel tests
python3 -m app.mutation_tests        # 10 mutation tests (90% kill)
python3 -m app.external_agent_tests  # 10 agent tests
python3 -m app.red_team_oracle       # 30 adversarial tests
python3 -m app.certify_utility       # Utility certification
python3 -m app.certify --profile production  # Full certification
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
| `AGENTS.md` | This file |
| `data/FRESH-AGENT-GUIDE.md` | Fresh agent guide |
| `data/HANDOVER-FINAL.md` | System map |
| `data/ORACLE-ARCHITECTURE.md` | Architecture |
| `data/DELL-ROADMAP.md` | Development roadmap |
| `data/PROVIDER-CATALOG.md` | Provider list |
| `data/TRUST-MODEL.md` | Trust model |
| `data/INVESTIGATION-PROTOCOL.md` | Discovery |
| `data/MONETIZATION.md` | Business model |
| `data/PEER-REVIEW-SYNTHESIS.md` | Review synthesis |
| `data/reports/DELL-EXTERNAL-UTILITY-AUDIT.md` | Audit report |

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

## Documentation Governance

### Single Source of Truth
**AGENTS.md is the single source of truth.** All other docs must reference it.

### How to Know What's Stale

1. **Check modification time**: Any doc not updated in 7+ days is suspect
2. **Check offer counts**: Current count is 1861 (as of 2026-08-18)
3. **Check feature status**: If doc says "not implemented", it's a future plan
4. **Check contradictions**: Any doc contradicting AGENTS.md is stale

### Conflict Resolution

| Doc Says | AGENTS.md Says | Status |
|----------|----------------|--------|
| 2463 offers | 1861 offers | STALE |
| 1714 models | 1714 models | CURRENT |
| 30 provenanced | 33% provenanced | CURRENT |
| "not implemented" | Feature status | FUTURE PLAN |

### Archive Policy

- Archive any doc not updated in 7+ days
- Archive any doc with stale references
- Keep only docs that are actively maintained
