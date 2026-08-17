# LLM Deals — Peer Review Brief

**For:** External review agent
**Date:** 2026-08-17
**Status:** Pre-git, needs objective review

## What This Is

LLM Deals is a canonical live data layer for LLM inference economics. It polls 38 sources, normalizes offers, scores them, and exposes everything via 5 APIs + MCP for agents to consume.

**Core claim:** "The highest-quality historical and real-time dataset of purchasable LLM inference opportunities."

## Architecture

```
38 Source Adapters → Snapshots (JSON) → Scoring Engine → 5 APIs → MCP (9 tools)
                                          ↓
                                   Kanban (4 boards)
                                          ↓
                                   Cron (every 6h)
```

## Key Files to Review

### Data Pipeline
- `app/sources/registry.py` — 38 source adapters registered
- `app/sources/opencode.py` — OpenCode Go adapter (extracts 2x multiplier)
- `app/sources/openrouter.py` — OpenRouter adapter (409 offers)
- `app/sources/artificial_analysis.py` — AA adapter (608 offers, rate-limited to 100/day)
- `app/sources/alibaba.py` — Alibaba adapter (246 offers, per-model quotas)
- `app/discovery.py` — Pipeline orchestrator
- `app/cron_poll.py` — Autonomous polling script

### Scoring & Categories
- `app/scoring.py` — 10-dimensional scoring vector + 21 badges
- `app/categories.py` — Workhorse, Value, Free, Fast, Agent, etc.
- `app/models_v2.py` — Data model (Model → ProviderOffering → CommercialOffer → DealEvent)
- `app/expiry.py` — Expiry tracking with hour-level precision
- `app/providers.py` — 15 providers with setup instructions

### APIs
- `app/api_canonical.py` — The boring useful data layer (port 8803)
- `app/api_v2.py` — Categories + providers (port 8800)
- `app/api_v3.py` — Scoring + badges (port 8801)
- `app/api_hot.py` — OpenAI-compatible router (port 8802)

### MCP & Hermes
- `mcp/server.mjs` — Node.js MCP server (9 tools)
- `~/.hermes/profiles/patala/skills/deal-scout/SKILL.md`
- `~/.hermes/profiles/patala/skills/deal-verifier/SKILL.md`
- `~/.hermes/profiles/patala/skills/deal-curator/SKILL.md`

### Specs & Docs
- `data/llmdeals.md` — V2 build spec (3553 lines)
- `data/apiuse.md` — Job-first taxonomy
- `data/llmrouting.md` — Hot Router spec
- `data/moreproviders.md` — Additional providers
- `data/internationalprovider.md` — Regional providers
- `data/concetratedvision.md` — Product vision
- `data/llmdealsintegration.md` — Architecture spec
- `docs/AGENT-GUIDE.md` — Agent integration recipes

### Test Results
- `data/tests/redteam-*.json` — Endpoint test logs
- `data/tests/final-validation-*.json` — System state

## Questions for Reviewer

### 1. Data Quality
- Are the 2762 offers real or are there duplicates/artifacts?
- The scoring vector (10 dimensions) — are the weights reasonable?
- Is "value" (intelligence/cost) the right metric for ranking?

### 2. Coverage Gaps
- 38 adapters registered, but many return 0 offers (akashml, nous-portal, ovhcloud, aethir)
- Is it better to have an adapter that returns 0 or not have it at all?
- Should we mark adapters as "verified working" vs "registered but untested"?

### 3. Known Deal Detection
- DeepSeek V4 Flash 2x on OpenCode Go: Our system NOW finds the 2x multiplier. But it's a general "2x usage promo" not linked to specific models. Is that sufficient?
- Nous Research 90% off: NOT found. The adapter returns 0 offers. Is this a parser issue or does the deal no longer exist?
- Luna on OpenCode Go: The page shows "GPT 5.6 Luna" with "2x usage" and "4,100" requests. Our parser extracts the multiplier but doesn't link it to Luna. Should it?

### 4. Architecture Concerns
- Is the 5-API architecture (V1/V2/V3/Hot/Canonical) too complex?
- Should we consolidate to fewer APIs?
- The Node.js MCP bridge — is this the right pattern or should we use Python MCP SDK?

### 5. What's Missing
- Expiry tracking shows 0 deals expiring — is the parsing working?
- Rate limits only on 568/2762 offers — should we enforce this?
- No historical deal changes yet (321 events but all from current snapshot)
- Activation class shows UNKNOWN for most offers

### 6. Agent Usability
- Can an external agent actually use the MCP tools to answer real questions?
- Are the tool descriptions clear enough?
- Is the data format what agents expect?

## Honest Self-Assessment

### What's Good
- Architecture is solid and extensible
- 38 source adapters cover a wide range of providers
- 2762 offers with 691 free — real data volume
- MCP + Kanban + Cron all working
- Agent docs with 10 recipes

### What Needs Work
- Many adapters return 0 offers (need debugging or removal)
- Expiry tracking not functional
- Multiplier deals (2x) extracted but not linked to specific models
- No historical trend data yet
- Rate limit coverage is sparse

### What's Unknown
- Whether the scoring actually produces useful rankings
- Whether agents can actually consume the data effectively
- Whether the source adapters will survive provider page changes
