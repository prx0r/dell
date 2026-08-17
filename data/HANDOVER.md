# LLM Deals — Handover Document

**Date:** 2026-08-17
**Status:** Foundation complete, ready for hardening phase
**Git:** master @ bbd1fd9

---

## What's Built

### Data Layer (the product)
- **38 source adapters** polling real APIs
- **2396 offers** in canonical SQLite DB
- **599 free offers** with utility scoring
- **31 providers** with setup instructions
- **37 claims** + **131 events** in canonical DB
- **Identity resolution** (EXACT_SAME_MODEL, SIBLING_VARIANT)
- **Deal classification** (132 deals vs 2272 catalog entries)
- **Mega deal detection** (MiMo 9.4x, Luna 2x, Kimi 2x)
- **Free qualification** (utility scoring by context + capabilities + rates)
- **Expiry tracking** (hour-level precision)
- **Live probing** (tests if endpoints work)

### APIs (5 surfaces, 61 endpoints)
- **V1** (8799): Original (deprecated)
- **V2** (8800): Categories + providers
- **V3** (8801): Scoring + badges
- **Hot** (8802): OpenAI-compatible router
- **Canonical** (8803): The data layer

### MCP (9 tools)
find_inference_deals, get_free_models, get_providers, get_provider_setup, get_best_by_badge, recommend_model, get_deal_changes, explain_deal, get_dataset_stats

### Testing
- **10/10 invariant tests** passing
- **52/54 API endpoints** passing (from earlier red team)
- **Hermes tested** — found MiMo 9.4x capacity deal

---

## What's NOT Done (Next Build Steps)

### Priority 1: Evidence Pipeline
- Wire discovery_claims.py into live discovery (partially done)
- Wire event_recorder.py into live discovery (partially done)
- Record ALL observations (currently only first)
- Store raw artifacts content-addressably

### Priority 2: Identity System
- Wire identity resolver into discovery
- Fix cross-reference (currently fuzzy name matching)
- Add proper identity assertions

### Priority 3: API Hardening
- MCP reads from DealService (currently reads snapshots)
- Split /deals (unusual) from /catalog (everything)
- Fix API filters (some accepted but not enforced)
- Add exponential backoff for source failures

### Priority 4: Scoring
- Fix reliability (hardcoded 70)
- Fix tool_calling defaults
- Separate raw metrics from derived scores
- Keep quota vectors intact (1500/5h ≠ 1500/day)

### Priority 5: CI/CD
- GitHub Actions for lint, test, invariant
- Protect main branch
- Gold fixture tests for OpenCode Go + Zen

---

## Architecture (target state)

```
                         EXTERNAL WORLD
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
        known sources       scouting         submissions
             │                 │                 │
             └─────────────────┬─────────────────┘
                               │
                             FETCH
                               │
                        immutable artifact
                               │
                          Observation
                               │
                        Candidate Claims
                               │
                  ┌────────────┴─────────────┐
                  │                          │
           deterministic                Hermes
             extraction              investigation
                  │                          │
                  └────────────┬─────────────┘
                               │
                        Identity Resolution
                               │
                           Evidence
                               │
                         Adjudication
                               │
                     append-only events
                               │
                         projections
                               │
                   ┌───────────┼───────────┐
                   │           │           │
                catalog      deals       history
                   │           │           │
                   └───────────┼───────────┘
                               │
                         DealService
                     ┌─────────┼─────────┐
                     │         │         │
                    API       MCP       SITE
```

---

## Files to Review Next Session

### Core (must understand)
- `app/discovery.py` — pipeline orchestrator
- `app/canonical_db.py` — SQLite kernel
- `app/service.py` — DealService
- `app/api_canonical.py` — canonical API
- `app/identity/resolver.py` — model identity

### New modules (need integration)
- `app/discovery_claims.py` — observation → claim
- `app/event_recorder.py` — deal events
- `app/candidate.py` — typed CandidateOffer
- `app/deal_classifier.py` — deals vs catalog
- `app/artifact_store.py` — raw artifacts
- `app/identity/transfer_rules.py` — field locality

### Data
- `data/DELL_FINAL_BUILD_BLUEPRINT.md` — the full spec
- `data/llmdeals.md` — V2 build spec
- `data/apiuse.md` — job-first taxonomy
- `data/llmrouting.md` — Hot Router spec
- `data/moreproviders.md` — additional providers
- `data/internationalprovider.md` — regional providers
- `data/concetratedvision.md` — product vision

---

## Key Decisions Made

1. **Data layer, not router** — LLM Deals is the canonical data source, not a router
2. **SQLite is canonical** — JSON exports, not the other way around
3. **Identity resolution** — EXACT_SAME_MODEL only propagates benchmarks
4. **Tri-state semantics** — FREE/PAID/UNKNOWN, not True/False
5. **Region=NULL** — unknown, NOT "global"
6. **Deals ≠ catalog** — only unusual opportunities in /deals
7. **Evidence must be traceable** — every claim has source URL
8. **Historical is append-only** — never delete, always append events

---

## Next Session Checklist

1. [ ] Wire discovery_claims.py → discovery.py (fully)
2. [ ] Wire event_recorder.py → discovery.py (fully)
3. [ ] Wire deal_classifier.py → API
4. [ ] Make MCP read from DealService
5. [ ] Fix exponential backoff for sources
6. [ ] Add /v1/deals/expiring with real data
7. [ ] Fix scoring reliability (hardcoded 70)
8. [ ] Add GitHub Actions CI
9. [ ] Gold fixture tests for OpenCode Go + Zen
10. [ ] Re-run Hermes random test
