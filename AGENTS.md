# LLM Deals — Agent Operating Manual

## Mission

> LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.

## Architecture

```
38 Source Adapters → Canonical SQLite → DealService → REST + MCP + Site
      ↓                                    ↓
  Observations                      /v1/catalog
      ↓                             /v1/deals
  Claims                            /v1/deals/hot
      ↓                             /v1/free
  Evidence                          /v1/models
      ↓                             /v1/providers
  Adjudication                      /v1/recommend
      ↓
  Append-only Events
      ↓
  Current Projections
```

## Key Files

| File | Purpose |
|------|---------|
| `app/discovery.py` | Pipeline orchestrator — polls sources, extracts, commits |
| `app/canonical_db.py` | SQLite kernel — all writes through this |
| `app/service.py` | DealService — one service for REST/MCP/site |
| `app/api_canonical.py` | Canonical API (port 8803) |
| `app/scoring.py` | 10-dimensional scoring + 21 badges |
| `app/identity/resolver.py` | Model identity resolution |
| `app/discovery_claims.py` | Observation → claim → evidence |
| `app/event_recorder.py` | Append-only deal events |
| `app/deal_classifier.py` | Deals vs catalog split |
| `app/mega_deals.py` | Institutional-quality deal detection |
| `app/free_qualification.py` | Free deal utility scoring |
| `app/candidate.py` | Typed CandidateOffer |
| `app/artifact_store.py` | Content-addressed raw artifacts |
| `app/history.py` | Historical snapshot comparison |
| `app/live_probe.py` | Live endpoint verification |
| `app/expiry.py` | Expiry tracking with precision |
| `mcp/server.mjs` | MCP server (9 tools, Node.js) |

## How to Run

```bash
# Full pipeline
python3 -m app.cron_poll --all

# Start API
python3 -m uvicorn app.api_canonical:app --port 8803

# Run invariant tests
python3 -m app.invariant_tests

# Hermes test
hermes -z "Use llm-deals MCP to find cheapest coding model"
```

## The DAG

```
Source Adapter
  → Observation (immutable)
  → Claim (extracted fact)
  → Evidence (provenance)
  → Adjudication
  → Domain Event (append-only)
  → Current Projection (API response)
```

## Identity Resolution

```
EXACT_SAME_MODEL → propagate benchmarks, context
SIBLING_VARIANT → do NOT propagate
SAME_MODEL_DIFFERENT_PROVIDER → may propagate context with evidence
```

## Scoring (10 dimensions)

Intelligence | Workhorse | Value | Coding | Agentic | Tool Calling | Research | Long Context | Speed | Reliability

## Deal Classification

A deal is NOT every cheap model. It's an UNUSUALLY favorable opportunity:
- Temporary free
- Usage multiplier (2x+)
- High capacity (3x+ baseline)
- Price anomaly
- Signup/startup credits
- Batch/off-peak discounts

Ordinary market-rate models stay in /catalog.

## Tri-State Semantics

```python
price_state: FREE | PAID | UNKNOWN  # never: False = UNKNOWN
automation_allowed: TRUE | FALSE | CONDITIONAL | UNKNOWN
region: NULL | country_code  # NULL = unknown, NOT "global"
```

## Invariants

1. Unknown price never becomes free
2. Unknown region never becomes global
3. Unknown terms never become allowed
4. One model can have N provider offerings
5. Raw observations can be replayed
6. Every claim has evidence
7. MCP and REST return identical results
8. Same input → same scoring output
9. Failed fetches don't expire deals
10. Source failures tracked separately from deal status

## Rules

- Read state before claiming: `python3 -m app.cron_poll --step state`
- Never skip the proposal: `python3 -m app.cron_poll --step propose`
- Commit only logged results
- No fabricated data — adapters must not invent facts
- Region=NULL means unknown, NOT global
- Price=NULL means unknown, NOT $0
- Free=False means unknown, NOT paid

## Kanban

| Board | Purpose |
|-------|---------|
| library-production | Main pipeline queue |
| library-scout | New deal discovery |
| library-verify | Deal verification |
| library-curate | Final curation + commit |
