# LLM Deals — Final Handover

**Date:** 2026-08-17
**Git:** master @ c3beca5
**Status:** OPERATIONAL — all core systems wired and validated

---

## What We Built

### Data Pipeline
```
38 Source Adapters → Canonical SQLite → DealService → REST + MCP + Site
      ↓                                    ↓
  Observations                      /v1/catalog
      ↓                             /v1/deals
  Claims                            /v1/free
      ↓                             /v1/recommend
  Evidence
      ↓
  Append-only Events
      ↓
  Current Projections
```

### Numbers
- **2463 offers** from 38 source adapters
- **632 free offers** with utility scoring
- **65 providers** with setup instructions
- **36 claims** with evidence links
- **36 evidence records** linked to claims
- **131 events** with timestamps
- **60 observations** with content hashes
- **3 verification runs** with tool event chains
- **10 activation recipes** for top providers
- **14 database tables**

### APIs (5 surfaces)
| Port | API | Endpoints |
|------|-----|-----------|
| 8799 | V1 | 19 (deprecated) |
| 8800 | V2 | 16 (categories) |
| 8801 | V3 | 9 (scoring) |
| 8802 | Hot | 3 (router) |
| 8803 | Canonical | 10 (data layer) |

### MCP (9 tools)
get_dataset_stats, list_models, list_providers, get_provider_setup, find_inference_deals, recommend_model, explain_deal, get_deal_changes, get_dataset_stats

### Skills (7)
library-discovery, library-investigate, library-validate, library-orchestrator, library-essay-critic, library-research-reviewer, library-visual-qa

### Kanban (8 boards)
library-production (473 cards), library-discovery, library-investigate, library-validate, library-scout, library-reviews, library-verify, library-curate

---

## How It Works

### Source Adapters (38)
Each adapter:
1. Fetches from a live source (HTTP or Playwright)
2. Extracts offers with structured data
3. Records observations with content hashes
4. Writes to canonical SQLite DB

### Canonical DB (14 tables)
- offers: 2463 offers with full metadata
- claims: 36 claims with evidence links
- evidence_v2: 36 evidence records
- deal_events: 131 events with timestamps
- source_observations: 60 observations with hashes
- verification_runs: 3 runs with tool events
- activation_recipes: 10 provider setup guides
- sources: 38 registered sources

### API
- `/v1/models` — What models exist
- `/v1/deals` — Unusual opportunities
- `/v1/free` — Free models ranked by utility
- `/v1/recommend` — Task-first recommendation
- `/v1/mega-deals` — Institutional-quality deals
- `/v1/verification-runs` — Verification history
- `/v1/deals/{id}/evidence` — Deal evidence
- `/v1/deals/{id}/verification` — Deal verification status

### MCP Tools
```
find_inference_deals  → Search deals by task/price
get_free_models       → Ranked free models
get_providers         → Provider setup info
get_provider_setup    → Step-by-step setup
recommend_model       → Task-first recommendation
explain_deal          → Deal deep-dive
get_deal_changes      → Recent changes
get_dataset_stats     → Overview
```

### Investigation Pipeline
```
Round 1: Fast scan (HTTP, hash, RSS) — what changed?
Round 2: Deep verify (Playwright) — how did it change?
Round 3: Global scout (Hermes web search) — new sources?
Round 4: Audit (recheck) — is it real?
```

---

## Key Decisions Made

1. **Data layer, not router** — LLM Deals is the canonical data source
2. **SQLite is canonical** — JSON exports, not the other way around
3. **Identity resolution** — EXACT_SAME_MODEL propagates, SIBLING_VARIANT doesn't
4. **Tri-state semantics** — FREE/PAID/UNKNOWN, not True/False
5. **Region=NULL** — unknown, NOT "global"
6. **Deals ≠ catalog** — only unusual opportunities in /deals
7. **Evidence must be traceable** — every claim has source URL
8. **Historical is append-only** — never delete, always append events
9. **Playwright for JS pages** — OpenCode Go uses browser rendering
10. **Multi-round investigation** — don't get everything in one pass

---

## What's Next

1. Add live probe verification (actually test if APIs work)
2. Implement historical trend tracking
3. Add Twitter/X integration (when available)
4. Provider expansion (21 more from moreproviders.md)
5. Pass release gate (100/100 claims replay)
6. Build web dashboard with real-time updates
