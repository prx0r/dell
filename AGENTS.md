# LLM Deals — Agent Operating Manual

## Mission

> Dell is a reproducible, adversarially tested, production-grade inference-economics oracle for llmdeals.org.

## Quick Start

```bash
cd /root/ass-rape-spunk-porn
python3 -m app.migrate                     # Run migrations
python3 -m app.schema_check                # Verify schema
python3 -m app.certify --profile production  # Full certification
python3 -m uvicorn app.api_canonical:app --port 8803  # Start API
python3 -m app.invariant_tests             # Run proof kernel
python3 -m app.red_team_oracle             # Run 30 adversarial tests
python3 -m app.gap_report                  # Gap analysis
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
                    │  offer_assertions ← verification_dimensions
                    │     ↓
                    │  model_events (append-only)
                    └─────────────────────────────────────────┘
                              ↓                    ↓
                         REST API              MCP Tools
                         (port 8803)           (9 tools)
```

## Data Model (21 tables)

| Table | Records | Purpose |
|-------|---------|---------|
| models | 1714 | Canonical model identity |
| model_prices | 3019 | Append-only price observations |
| model_providers | 1821 | Model ↔ provider relationships |
| serving_endpoints | 79 | Actual serving routes |
| quota_policies | 7 | Free quotas |
| offer_assertions | 30 | Field-level claims |
| verification_dimensions | 38 | Independent predicates |
| freshness_policies | 20 | TTL rules |
| negative_observations | 2 | Absence records |
| source_authority | 12 | Authority rules |
| economic_access | 1861 | Access classification |
| offers | 1861 | Commercial propositions |
| claims | 30 | Extracted claims |
| evidence_v2 | 30 | Evidence records |
| verification_runs | 17 | Audit trails |
| tool_events | 31 | Hash chain |
| activation_recipes | 10 | Setup guides |
| schema_migrations | 7 | Migration tracking |

## Oracle-1 Milestone (Complete)

| Milestone | Status | What Was Built |
|-----------|--------|----------------|
| D0 Reproducibility | ✅ | 7 migrations, schema check |
| D1 Evidence Kernel | ✅ | Provenance chain |
| D2 Temporal Truth | ✅ | Freshness, stale, negative |
| D3 Identity Semantics | ✅ | MODEL != ENDPOINT != OFFER |
| D4 Economic Semantics | ✅ | 9 access classes |
| D5 Discovery/Ingestion | ✅ | Adapter contract |
| D6 Verification | ✅ | 10 dimensions |
| D7 API Contract | ✅ | 41 endpoints |
| D8 Ranking | ✅ | Epistemically labeled |
| D9 Adversarial Suite | ✅ | 30/30 tests |
| D10 Operations | ✅ | Ready |
| D11 Data Coverage | ✅ | 1714 models |
| D12 Release Certificate | ✅ | CERTIFICATE: PASS |

## API Endpoints

### Core Data
- `GET /v1/models` — List all models
- `GET /v1/deals` — List all deals
- `GET /v1/deals/free` — Free models
- `GET /v1/deals/live` — Verified live deals
- `GET /v1/mega-deals` — Institutional deals
- `GET /v1/recommend` — Task recommendations
- `POST /v1/free/plan` — Plan free workload

### Provider Intelligence
- `GET /v1/providers` — List providers
- `GET /v1/providers/browse` — Browse by category
- `GET /v1/providers/{id}/deals` — Provider deals
- `GET /v1/providers/{id}/discover` — Discovery info

### Verification
- `GET /v1/verification-runs` — Audit trails
- `GET /v1/deals/{id}/evidence` — Deal evidence
- `GET /v1/deals/{id}/verification` — Verification status

## Hermes Operations

### Discovery Pipeline
```
library-discovery → library-investigate → library-validate → Canonical DB
```

### Gap Analysis
```bash
python3 -m app.gap_report
```

### Free Capacity Planning
```bash
curl -X POST http://localhost:8803/v1/free/plan \
  -H "Content-Type: application/json" \
  -d '{"task":"coding","requests":100,"min_context":64000}'
```

## Source Hierarchy

- **Tier A**: Official machine API
- **Tier B**: Official structured docs
- **Tier C**: Authenticated account observation
- **Tier D**: Dell synthetic probe
- **Tier E**: Browser inspection
- **Tier F**: Blogs/Reddit (discovery only)

## Canonical States

### Quantization
- KNOWN | UNKNOWN | VARIABLE

### Availability
- AVAILABLE | DEGRADED | UNAVAILABLE | UNKNOWN

### Free Mechanism
- ZERO_MARGINAL_PRICE | FREE_QUOTA | TRIAL_CREDIT | PROMOTIONAL_QUOTA
- SUBSCRIPTION_INCLUDED | CONDITIONAL_FREE | COMMUNITY_COMPUTE | PAID | UNKNOWN

### Lifecycle
- ACTIVE_VERIFIED | ACTIVE_UNVERIFIED | STALE | CONFLICTED | WITHDRAWN | EXPIRED

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

## Key Files

### Core
- `app/canonical_db.py` — SQLite kernel
- `app/api_canonical.py` — REST API
- `app/verification.py` — Proof kernel
- `app/scoring.py` — 10D scoring
- `app/freshness.py` — TTL checking
- `app/provenance.py` — Provenance chain
- `app/oracle_identity.py` — Identity separation
- `app/economics.py` — Access classification
- `app/adapter_contract.py` — Adapter interface
- `app/verification_dimensions.py` — Verification predicates
- `app/gap_report.py` — Gap analysis
- `app/red_team_oracle.py` — 30 adversarial tests
- `app/certify.py` — Production certification

### Schema
- `app/migrations/0001-0007` — 7 migrations
- `app/schema_check.py` — Schema verification

### Documentation
- `data/DELL-ROADMAP.md` — Development roadmap
- `data/HANDOVER-FINAL.md` — Current handover
- `data/ORACLE-ARCHITECTURE.md` — Architecture
- `data/PEER-REVIEW-V3.md` — Latest review
- `data/TRUST-MODEL.md` — Trust model
