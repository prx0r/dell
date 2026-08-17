# LLM Deals — Agent Operating Manual

## Mission

> LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.

## Quick Start

```bash
cd /root/ass-rape-spunk-porn
python3 -m app.cron_poll --all                    # Poll all 38 sources
python3 -m uvicorn app.api_canonical:app --port 8803  # Start API
python3 -m app.invariant_tests                     # Run tests
```

## Architecture

```
38 Source Adapters → Canonical SQLite → DealService → REST + MCP + Site
```

## Key Files (in review order)

### Start Here
1. `README.md` — what this project is
2. `AGENTS.md` — this file (operating manual)
3. `data/HANDOVER-FINAL.md` — complete system map
4. `data/INVESTIGATION-PROTOCOL.md` — how discovery works

### Core Pipeline
5. `app/discovery.py` — pipeline orchestrator
6. `app/canonical_db.py` — SQLite kernel (all writes)
7. `app/service.py` — DealService (one service for all)
8. `app/api_canonical.py` — canonical API (port 8803)
9. `app/scoring.py` — 10D scoring + 21 badges

### Data Model
10. `app/models_v2.py` — Model → ProviderOffering → CommercialOffer → DealEvent
11. `app/identity/resolver.py` — model identity (EXACT_SAME_MODEL etc)
12. `app/deal_classifier.py` — deals vs catalog
13. `app/mega_deals.py` — institutional-quality deals
14. `app/free_qualification.py` — free deal utility

### Evidence Pipeline
15. `app/discovery_claims.py` — observation → claim
16. `app/event_recorder.py` — append-only events
17. `app/verification.py` — VerificationRun + tool events
18. `app/artifact_store.py` — content-addressed storage
19. `app/source_diff.py` — change detection

### Source Adapters (38)
20. `app/sources/registry.py` — source registry
21. `app/sources/opencode.py` — OpenCode Go (uses playwright)
22. `app/sources/openrouter.py` — OpenRouter (real-time pricing)
23. `app/sources/models_dev.py` — models.dev (benchmarks)
24. `app/sources/artificial_analysis.py` — AA (intelligence scores)
25. `app/sources/hf_router.py` — HuggingFace Router
26. `app/sources/rss.py` — RSS (8 blogs)
27. `app/sources/hackernews.py` — Hacker News
28. + 20 more adapters in app/sources/

### Skills
29. `~/.hermes/profiles/patala/skills/library-discovery/` — search for NEW deals
30. `~/.hermes/profiles/patala/skills/library-investigate/` — deep-dive into deals
31. `~/.hermes/profiles/patala/skills/library-validate/` — verify deals still active
32. `~/.hermes/profiles/patala/skills/llm-deal-radar/` — master driver skill

### Specs
33. `data/LLM_DEALS_VERIFICATION_ENGINE_BUILD_SPEC.md` — verification engine (1868 lines)
34. `data/llmdeals.md` — V2 build spec
35. `data/apiuse.md` — job-first taxonomy
36. `data/llmrouting.md` — Hot Router spec
37. `data/PRODUCT-VISION.md` — 5 products + monetization
38. `data/INTEGRATION-SPEC.md` — how to integrate alternatives

### Stale/Legacy (labeled but kept)
- `app/api.py` — DEPRECATED (use api_canonical.py)
- `app/api_v2.py` — DEPRECATED
- `app/api_v3.py` — DEPRECATED
- `app/api_hot.py` — DEPRECATED
- `app/normalize.py` — LEGACY (use scoring.py)
- `app/quality.py` — LEGACY
- `app/routing.py` — LEGACY
- `app/test*.py` — OLD_TEST (use invariant_tests.py)

---

## Pipeline Stages

### 1. Discovery (library-discovery skill)
```
Search web → find new providers → output SourceCandidate
```

### 2. Investigation (library-investigate skill)
```
New deal found → search all sources → extract details → record evidence
```

### 3. Validation (library-validate skill)
```
Deal identified → check official source → verify still active → record status
```

### 4. Canonical DB
```
Observation → Claim → Evidence → Verification → Offer → Event
```

---

## Rules

1. **Read state before claiming**: `python3 -m app.cron_poll --step state`
2. **Never skip the proposal**: always show cost/time before dispatch
3. **No fabricated data**: adapters must not invent fallback facts
4. **Region=NULL means unknown**, NOT global
5. **Price=NULL means unknown**, NOT $0
6. **Free=False means unknown**, NOT paid
7. **Every claim needs a source observation**
8. **Unknown remains unknown** — never coerce to certainty
9. **Historical is append-only** — never delete, always append
10. **Evidence is mandatory** — every deal links to source evidence
