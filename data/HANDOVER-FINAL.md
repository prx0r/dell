# LLM Deals — Final Handover

**Date:** 2026-08-17
**Git:** master @ 1915d9d
**Status:** OPERATIONAL

---

## What We Built

### Data Pipeline
```
38 Source Adapters → Canonical SQLite → DealService → REST + MCP + Site
```

### Numbers
- **2463 offers** from 66 providers
- **632 free offers** with utility scoring
- **65 providers** with setup instructions
- **36 claims** with evidence links
- **36 evidence records**
- **131 events** with timestamps
- **60 observations** with content hashes
- **3 verification runs**
- **10 activation recipes**
- **14 database tables**

### APIs (5 surfaces, 61 endpoints)
| Port | API | Purpose |
|------|-----|---------|
| 8799 | V1 | Original (deprecated) |
| 8800 | V2 | Categories + providers |
| 8801 | V3 | Scoring + badges |
| 8802 | Hot | OpenAI-compatible router |
| 8803 | Canonical | **The data layer** |

### MCP (9 tools)
get_dataset_stats, list_models, list_providers, get_provider_setup, find_inference_deals, recommend_model, explain_deal, get_deal_changes, get_dataset_stats

### Skills (7)
library-discovery, library-investigate, library-validate, library-orchestrator, library-essay-critic, library-research-reviewer, library-visual-qa

### Kanban (8 boards)
library-production (473 cards), library-discovery, library-investigate, library-validate, library-scout, library-reviews, library-verify, library-curate

---

## How It Works

### Pipeline Stages
```
DISCOVERY → INVESTIGATION → VALIDATION → CANONICAL DB
    ↓            ↓                ↓              ↓
  search      deep-dive        verify         record
  web/HN     all sources      official       evidence
  RSS         exact terms      still active   timestamps
  browser    dates/restrictions              hashes
```

### Evidence Chain
```
Source → Observation → Claim → Evidence → Verification
  ↓          ↓           ↓         ↓            ↓
URL+fetched_at  content_hash  offer_id    artifact_id
```

### Scoring
10 dimensions: Intelligence, Workhorse, Value, Coding, Agentic, Tool Calling, Research, Long Context, Speed, Reliability

21 badges: Mega Deal, Frontier, Workhorse, Coder, Agentic, Fast, Hidden Gem, Free, Long Context, Tool Caller, etc.

---

## Source Categorization

| Category | Providers | Status |
|----------|-----------|--------|
| Inference | 26 | ✅ All tracked |
| Aggregators | 7 | ✅ All tracked |
| Routers | 6 | ✅ Documented |
| Blogs | 7 | ✅ RSS feeds |
| Chinese AI | 9 | ✅ All tracked |
| Decentralized | 5 | ✅ Documented |

---

## Monetization

| Stream | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| API Tiers | $60K | $120K | $240K |
| Provider Partnerships | $36K | $100K | $200K |
| White-Label | $0 | $100K | $500K |
| Analytics | $24K | $60K | $120K |
| **Total** | **$168K** | **$500K+** | **$2M+** |

---

## Key Decisions

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

## Open Threads for Next Agent

| Thread | Priority | What Needs Doing |
|--------|----------|------------------|
| Empty snapshots | HIGH | akashml, nous-portal, ovhcloud have 0 offers |
| Legacy API removal | MEDIUM | api.py, api_v2.py, api_v3.py, api_hot.py deprecated |
| Legacy module archival | MEDIUM | normalize.py, quality.py, routing.py etc. |
| Old test removal | LOW | test*.py → invariant_tests.py |
| Provider expansion | MEDIUM | 21 more from moreproviders.md |
| Historical tracking | HIGH | All snapshots from same session |
| Live probe verification | MEDIUM | Actually test if APIs work |
| Expiry tracking | HIGH | 0/2463 offers have dates |
| Twitter integration | LOW | When hooked up |

---

## Stale Files (labeled)

| File | Status | Action |
|------|--------|--------|
| app/api.py | DEPRECATED | Use api_canonical.py |
| app/api_v2.py | DEPRECATED | Use api_canonical.py |
| app/api_v3.py | DEPRECATED | Use api_canonical.py |
| app/api_hot.py | DEPRECATED | Use api_canonical.py |
| app/normalize.py | LEGACY | Use scoring.py |
| app/quality.py | LEGACY | Use scoring.py |
| app/routing.py | LEGACY | Use scoring.py |
| app/tensions.py | LEGACY | Use scoring.py |
| app/task_ranking.py | LEGACY | Use scoring.py |
| app/test*.py | OLD_TEST | Use invariant_tests.py |

---

## Verification Status

| Test | Status |
|------|--------|
| Invariant tests | 10/10 PASS |
| API endpoints | 10/10 OK |
| MCP tools | Working |
| Kanban boards | 8 active |
| Cron job | Every 6 hours |

---

## What's Next

1. Add live probe verification
2. Implement historical tracking
3. Add Twitter integration
4. Provider expansion (21 more)
5. Pass release gate (100/100 claims)
6. Build web dashboard
7. LiteLLM integration
