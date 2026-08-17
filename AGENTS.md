# LLM Deals — Agent Operating Manual

## What This Is

LLM Deals is a canonical data layer for LLM inference economics. It aggregates pricing, deals, quotas, and promotions from 38 sources and exposes them via API, MCP, and a static site.

**North-star sentence:**
> LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.

## Quick Start

```bash
cd /root/ass-rape-spunk-porn
python3 -m app.cron_poll --all     # Poll all 38 sources
python3 -m uvicorn app.api_canonical:app --port 8803  # Start API
python3 -m app.invariant_tests     # Run tests
```

## Architecture

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

## How to Use as an Agent

### Via MCP (recommended)
```
find_inference_deals(task=coding, limit=5)
get_free_models(limit=10)
get_provider_setup(provider=openrouter)
recommend_model(task=coding, tool_calling=true)
explain_deal(model=opencode-go/gpt-5.6-luna)
```

### Via REST API
```bash
curl localhost:8803/v1/deals/free?limit=5
curl localhost:8803/v1/recommend?task=coding
curl localhost:8803/v1/providers
```

### Via Kanban
```bash
hermes kanban --board library-discovery claim
hermes kanban --board library-investigate claim
hermes kanban --board library-validate claim
```

## Skills

| Skill | Purpose |
|-------|---------|
| library-discovery | Search for NEW deals not in database |
| library-investigate | Deep-dive into specific deals |
| library-validate | Verify deals are still active |
| library-orchestrator | Drive the pipeline |

## Rules

1. Read state before claiming: `python3 -m app.cron_poll --step state`
2. Never skip the proposal
3. Commit only logged results
4. No fabricated data
5. Region=NULL means unknown, NOT global
6. Price=NULL means unknown, NOT $0
7. Free=False means unknown, NOT paid
8. Every claim must have a source observation

## Key Files

| File | Purpose |
|------|---------|
| `app/discovery.py` | Pipeline orchestrator |
| `app/canonical_db.py` | SQLite kernel |
| `app/service.py` | DealService |
| `app/api_canonical.py` | Canonical API (port 8803) |
| `app/scoring.py` | 10D scoring + 21 badges |
| `app/identity/resolver.py` | Model identity |
| `mcp/server.mjs` | MCP server (9 tools) |
| `data/HANDOVER.md` | Full handover document |
