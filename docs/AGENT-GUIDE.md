# LLM Deals — Agent Integration Guide

**The canonical live data layer for LLM inference economics.**

## Quick Start for Agents

### MCP Tools (recommended)

Register the MCP server:
```bash
hermes mcp add llm-deals --command node --args /root/ass-rape-spunk-porn/mcp/server.mjs
```

Available tools:
| Tool | What it does | Key params |
|------|-------------|------------|
| `find_inference_deals` | Search deals | `task`, `max_price`, `free_only`, `limit` |
| `get_free_models` | List free offers | `limit` |
| `get_providers` | All providers + setup | — |
| `get_provider_setup` | Step-by-step setup | `provider` |
| `get_best_by_badge` | Category ranking | `badge` (workhorse/coder/agentic/free/fast), `limit` |
| `recommend_model` | Task-first recommendation | `task`, `max_cost`, `tool_calling`, `min_context` |
| `get_deal_changes` | Recent changes | `since_hours` |
| `explain_deal` | Deal details + alternatives | `model`, `provider` |
| `get_dataset_stats` | Dataset overview | — |

### REST API

| Port | API | Base URL |
|------|-----|----------|
| 8799 | V1 (original) | `http://localhost:8799` |
| 8800 | V2 (categories) | `http://localhost:8800` |
| 8801 | V3 (scoring) | `http://localhost:8801` |
| 8802 | Hot Router | `http://localhost:8802` |
| 8803 | Canonical | `http://localhost:8803` |

## Agent Recipes

### Recipe 1: "Find me the cheapest coding model"

```bash
# MCP
find_inference_deals(task="coding", max_price=0.5, limit=5)

# REST
curl localhost:8803/v1/cheapest?task=coding_agent&limit=5
```

### Recipe 2: "What's free right now?"

```bash
# MCP
get_free_models(limit=10)

# REST
curl localhost:8803/v1/deals/free?limit=10
```

### Recipe 3: "How do I set up OpenRouter?"

```bash
# MCP
get_provider_setup(provider="openrouter")

# REST
curl localhost:8800/providers/openrouter/setup
```

### Recipe 4: "Best model for agentic coding with tool calling"

```bash
# MCP
recommend_model(task="coding", tool_calling=true, min_context=128000)

# REST
curl "localhost:8801/v1/recommend?task=coding_task&tool_calling=true&min_context=128000"
```

### Recipe 5: "What deals changed in the last 24h?"

```bash
# MCP
get_deal_changes(since_hours=24)

# REST
curl localhost:8803/v1/history?limit=20
```

### Recipe 6: "Compare MiMo across all providers"

```bash
# MCP
explain_deal(model="mimo", provider=null)

# REST
curl "localhost:8803/v1/prices?model=mimo"
```

### Recipe 7: "Best workhorse for batch extraction"

```bash
# MCP
get_best_by_badge(badge="worker", limit=5)

# REST
curl localhost:8801/best/worker?limit=5
```

### Recipe 8: "What's the deal score for Gemini Flash?"

```bash
# REST
curl localhost:8801/v1/score/google/gemini-3-7-flash
```

### Recipe 9: "Build me an agent stack for $1"

```bash
# REST
curl "localhost:8801/v1/stacks?task=agentic_coding&budget=1.0"
```

### Recipe 10: "What's the effective cost per coding task?"

```bash
# REST
curl "localhost:8803/v1/economics?task=coding_agent&limit=10"
```

## Source Polling (autonomous)

The system polls 17 sources via cron every 6 hours:

| Source | Cadence | What |
|--------|---------|------|
| OpenCode Go | 2h | Pricing, 2× promos |
| OpenCode Zen | 4h | Free API models |
| Nous Portal | 2h | Catalog, plans |
| OpenRouter | 6h | Prices, free models |
| models.dev | 24h | Capabilities |
| Artificial Analysis | 24h | Intelligence scores |
| HuggingFace Router | 24h | Per-provider pricing |
| Vercel Changelog | 2h | Launch pricing |
| HN | 2h | Community leads |
| RSS (8 blogs) | 2h | Deal announcements |
| SenseNova | 4h | $0 public beta |
| Sakura AI | 24h | 3K req/month |
| Scaleway | 24h | 1M tokens free |
| OVHcloud | 24h | $200 signup credits |
| Z.AI | 4h | GLM Flash free |
| Alibaba | 24h | Per-model quotas |
| AkashML | 24h | $100 signup credits |

### Rate Limits (be polite)

| Source | Rate Limit | Our Cadence |
|--------|-----------|-------------|
| Artificial Analysis | 100 req/day (free) | 24h (~8 calls/day) |
| OpenRouter | No documented limit | 6h |
| models.dev | No documented limit | 24h |
| HuggingFace Router | No documented limit | 24h |
| HN Firebase | No documented limit (be polite <1req/s) | 2h |
| RSS feeds | No documented limit | 2h |

**Total daily API budget: ~150-200 calls** (well within limits)

## Kanban Workflow

### Boards

| Board | Purpose |
|-------|---------|
| `library-production` | Main essay/offer pipeline |
| `library-scout` | New deal discovery candidates |
| `library-verify` | Deal verification queue |
| `library-curate` | Final curation + commit |

### Card Lifecycle

```
triage → todo → ready → running → done
                                → blocked (needs human)
```

### Creating Cards

```bash
hermes kanban --board library-scout create "SCOUT: SenseNova $0 beta" --body "Candidate: SenseNova public beta, 1500 calls/5h"
hermes kanban --board library-verify create "VERIFY: SenseNova" --body "Verify SenseNova $0 beta is still active"
hermes kanban --board library-curate create "COMMIT: SenseNova free tier" --body "Commit verified deal to canonical DB"
```

### Agent Execution

```bash
# Scout finds a deal
hermes kanban --board library-scout claim
# Work on it
hermes kanban --board library-scout complete <task_id>
# Move to verification
hermes kanban --board library-verify create "VERIFY: <deal>" --body "<details>"
```

## Cron Integration

```bash
# Poll all sources every 6 hours
hermes cron create "llm-deals-poll" --schedule "0 */6 * * *" \
  --command "cd /root/ass-rape-spunk-porn && python3 -m app.cron_poll" \
  --skill deal-scout

# Scout for new deals every 2 hours
hermes cron create "llm-deals-scout" --schedule "0 */2 * * *" \
  --command "cd /root/ass-rage-spunk-porn && hermes -z 'Search for new LLM deals using deal-scout skill' --skill deal-scout" \
  --skill deal-scout
```

## Data Model

```
Model → ProviderOffering → CommercialOffer → DealEvent
```

Each DealEvent has:
- `event_id` (content-addressed)
- `verification_status` (verified/likely/community_reported/unverified)
- `confidence` (0-1)
- `source_url` + `source_language`
- `eligibility` (regions, KYC, card required)
- `activation_class` (ZERO_TOUCH/KEY_ONLY/SIGNUP/VERIFY/PAYMENT/SUBSCRIPTION/KYC/APPLICATION/REGION_LOCKED)
- `freshness_sla` (last_verified, next_check, is_stale)

## Activation Classes

| Class | Meaning | Agent can automate? |
|-------|---------|-------------------|
| ZERO_TOUCH | Directly usable | Yes |
| KEY_ONLY | Needs API key | Yes (with user's key) |
| SIGNUP | Needs account | Partially |
| VERIFY | Email/phone needed | No (human) |
| PAYMENT_METHOD | Card needed | No (human) |
| SUBSCRIPTION | Plan needed | No (human) |
| KYC | Identity verification | No (human) |
| APPLICATION | Startup/grant app | No (human) |
| REGION_LOCKED | Region dependent | Check eligibility |

## Anti-Failsafes

1. **Source failure ≠ deal ended.** Parser errors create "source degraded" not "deal expired."
2. **Community ≠ verified.** Reddit posts are leads, not facts. Always verify against official sources.
3. **Unknown ≠ free.** Missing prices are NULL, never zero.
4. **History is immutable.** Never overwrite — append new events.
5. **Freshness SLA.** Every result includes when it was last verified and when next check is due.
6. **Confidence levels.** VERIFIED > LIKELY > COMMUNITY_REPORTED > UNVERIFIED. Agents can filter by minimum confidence.
