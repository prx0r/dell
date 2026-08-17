# LLM Deals — Complete Handover

**Date:** 2026-08-17
**Git:** master @ 1e16bdf
**Status:** OPERATIONAL — all core systems wired and validated

---

## What's Built

### Data Pipeline
```
38 Source Adapters → Canonical SQLite → DealService → REST + MCP + Site
```

| Component | Status | Detail |
|-----------|--------|--------|
| Source adapters | ✓ | 38 adapters, 36 return data |
| Canonical DB | ✓ | 1853 offers, 632 free, 65 providers |
| Claims | ✓ | 33 claims with confidence scores |
| Events | ✓ | 131 events with timestamps |
| Observations | ✓ | 59 observations with HTTP status |
| Source scheduler | ✓ | 38 sources registered, persistent state |
| Identity resolver | ✓ | EXACT_SAME_MODEL, SIBLING_VARIANT |
| Deal classifier | ✓ | 132 deals vs catalog |
| Mega deal detection | ✓ | MiMo 9.4x, Luna 2x, Kimi 2x |
| Free qualification | ✓ | Utility scoring by context/capabilities/rates |
| Expiry tracking | ✓ | Hour-level precision |
| Live probing | ✓ | Tests if endpoints work |

### APIs
| Port | Endpoints | Purpose |
|------|-----------|---------|
| 8799 | 19 | V1 (deprecated) |
| 8800 | 16 | V2 categories |
| 8801 | 9 | V3 scoring |
| 8802 | 3 | Hot router |
| 8803 | 12 | Canonical data layer |

### MCP
- 9 tools registered with Hermes
- Reads from DealService (canonical DB)
- Tools: get_dataset_stats, list_models, list_providers, get_provider_setup, find_inference_deals, recommend_model, explain_deal, get_deal_changes, get_dataset_stats

### Kanban
- library-production: 473 cards
- library-scout: 1 card
- library-verify: empty
- library-curate: empty

### Testing
- 10/10 invariant tests PASS
- 12/12 API endpoints PASS
- 38/38 source adapters OK
- Hermes tested — found DeepSeek as best deal

---

## File Map

### Core Pipeline
- `app/discovery.py` — pipeline orchestrator
- `app/canonical_db.py` — SQLite kernel
- `app/service.py` — DealService
- `app/discovery_claims.py` — observation → claim
- `app/event_recorder.py` — deal events
- `app/candidate.py` — typed CandidateOffer
- `app/deal_classifier.py` — deals vs catalog

### Identity & Scoring
- `app/identity/resolver.py` — model identity
- `app/identity/transfer_rules.py` — field locality
- `app/scoring.py` — 10 dimensions + 21 badges
- `app/mega_deals.py` — institutional-quality deals
- `app/free_qualification.py` — free deal utility

### APIs
- `app/api_canonical.py` — canonical data layer (port 8803)
- `app/api_v2.py` — categories (port 8800)
- `app/api_v3.py` — scoring (port 8801)
- `app/api_hot.py` — router (port 8802)

### MCP
- `mcp/server.mjs` — Node.js MCP (9 tools, DealService-backed)

### Data
- `data/DELL_FINAL_BUILD_BLUEPRINT.md` — full spec
- `data/llmdeals.md` — V2 build spec
- `data/apiuse.md` — job-first taxonomy
- `data/llmrouting.md` — Hot Router spec
- `data/moreproviders.md` — additional providers
- `data/internationalprovider.md` — regional providers
- `data/concetratedvision.md` — product vision
- `data/HANDOVER.md` — previous handover
- `data/FINAL-STATUS.md` — status summary
- `data/COMPLETE-HANDOVER.md` — this file

### Tests
- `app/invariant_tests.py` — 10 invariants
- `data/tests/redteam-*.json` — red team results
- `data/tests/hermes-user-test.md` — Hermes feedback

---

## Next Build Steps

### Priority 1 (Hardening)
1. Add exponential backoff for source failures
2. Add /v1/deals/expiring with real data
3. Fix scoring reliability (hardcoded 70)
4. Wire MCP into Hermes kanban workflow

### Priority 2 (Features)
5. Add GitHub Actions CI
6. Gold fixture tests for OpenCode Go + Zen
7. Provider expansion (21 more from moreproviders.md)
8. Add activation recipes for providers

### Priority 3 (Polish)
9. Historical trend tracking
10. Web dashboard updates
11. Documentation improvements

---

## How to Use

### As an Agent
```bash
hermes -z "Use llm-deals MCP to find cheapest coding model"
```

### As a Developer
```bash
python3 -m app.cron_poll --all     # Poll sources
python3 -m uvicorn app.api_canonical:app --port 8803  # API
curl localhost:8803/v1/deals/free?limit=5              # Quick query
```

### As a Hermes User
```
hermes kanban --board library-production list
hermes kanban --board library-scout claim
hermes kanban --board library-scout complete <id>
```
