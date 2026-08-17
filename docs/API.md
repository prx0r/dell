# Deal Radar V2 — Agentic API Documentation

**The LLM inference aggregator. CoinGecko for AI compute.**

Base URL: `http://localhost:8800`
Source: `/root/ass-rape-spunk-porn/`
Data: 1413+ offers from 17 sources, updated daily

## Quick Start

```bash
# Run discovery (poll all sources)
cd /root/ass-rape-spunk-porn && python3 -m app.poll --all

# Start the API
python3 -m uvicorn app.api_v2:app --host 0.0.0.0 --port 8800

# Or test it
python3 -c "import sys; sys.path.insert(0,'app'); from api_v2 import app; import uvicorn; uvicorn.run(app, port=8800)"
```

## Endpoints

> **Note:** This documents API v2 (`app/api_v2.py`). Other API versions exist: v1 (`app/api.py`, port 8799), v3 (`app/api_v3.py`), canonical (`app/api_canonical.py`), and hot-proxy (`app/api_hot.py`).

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | API health check |

### Deals

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/deals/hot?limit=20` | GET | Hottest deals scored by deal_score (discount + quality + rate limits + urgency) |
| `/deals/free?limit=20` | GET | Currently free models ranked by daily capacity |
| `/deals/expiring?hours=24&limit=20` | GET | **Precise expiry tracking** — offers expiring within N hours with countdown |
| `/deals/expired?limit=20` | GET | Recently expired deals |
| `/deals/changes` | GET | Recent price/promo changes |
| `/deals/workhorses?workload=coding_agent&limit=10` | GET | Best value for specific workload |

### Categories

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/categories` | GET | List all 8 categories |
| `/categories/{name}?limit=15` | GET | Get category (workhorse/value/easy/free/fast/vision/agents/providers) |

### Providers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/providers` | GET | Full provider comparison (14 providers) |
| `/providers/{id}` | GET | Provider detail — setup difficulty, features, pricing model |
| `/providers/{id}/setup` | GET | **Step-by-step setup instructions** — exact steps to claim the deal |

### Workload

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/workload/{name}?limit=10` | GET | Best models for a workload (coding_agent/batch_extraction/interactive_chat/translation/research) |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Overall stats (total offers, free count, providers) |
| `/sources/health` | GET | Source health — which sources are polling successfully |
| `/events?limit=50` | GET | Recent promotion events |

## Categories (the CoinGecko layer)

| ID | Name | What It Scores |
|----|------|----------------|
| `workhorse` | Best Workhorse | 35% cost + 25% capabilities + 20% context + 20% daily capacity |
| `value` | Best Value Ratio | Intelligence (from AA index) / cost per 1M tokens |
| `easy` | Easiest to Get | Sorted by setup difficulty (1=instant, 4=enterprise) |
| `free` | Best Free Tier | Ranked by actual daily capacity (req/day + tokens/day) |
| `fast` | Fastest Inference | Sorted by latency (ms) |
| `vision` | Best for Vision | Image-capable models sorted by cost |
| `agents` | Best for Agents | Tool calling + structured output + reliability |
| `providers` | Provider Comparison | Side-by-side: setup, free tier, features, T&C |

## Workload Types

| Workload | Tokens/Job | Jobs/Day | Quality Floor | Description |
|----------|-----------|----------|---------------|-------------|
| `coding_agent` | 5000 | 100 | 60 | Agentic coding tasks, large batch |
| `batch_extraction` | 1000 | 500 | 40 | High-volume data extraction |
| `interactive_chat` | 500 | 50 | 70 | Real-time chat, low latency |
| `translation` | 2000 | 200 | 50 | Translation, moderate quality |
| `research` | 3000 | 30 | 80 | Deep research, high quality |

## Expiry Tracking

The `/deals/expiring` endpoint provides **hour-level precision**:

```json
{
  "deals": [{
    "model_id": "openai/gpt-4o",
    "expiry": {
      "expires_at": "2026-08-17T12:00:00Z",
      "hours_remaining": 3.5,
      "status": "expiring_soon",
      "precision": "date"
    },
    "countdown": "3.5h left",
    "verification": {
      "status": "verified",
      "confidence": 0.85,
      "reason": "Confirmed by 2 sources"
    }
  }]
}
```

**Expiry statuses:**
- `active` — deal is live, > 24h remaining
- `expiring_soon` — < 24h remaining
- `expiring_imminent` — < 4h remaining
- `expired` — past expiry date
- `unknown` — no expiry date tracked

**Precision levels:**
- `date` — exact date from provider ("ends Dec 31, 2026")
- `relative` — computed from text ("3 days left")
- `iso` — ISO timestamp from API
- `vague` — "limited time" (no precise date)
- `none` — no expiry info

## Provider Setup Difficulty

| Level | Meaning | Example |
|-------|---------|---------|
| 1 | Instant — API key only, no approval | OpenRouter, Groq, DeepSeek |
| 2 | Account required — sign up + verify | Anthropic, OpenAI, Cloudflare |
| 3 | Approval needed — wait for access | Enterprise providers |
| 4 | Enterprise — contract required | Custom |

## Source Polling

| Source | Cadence | What It Polls | Rate Limit | Spec Ref |
|--------|---------|--------------|------------|----------|
| OpenRouter | 6h | `/api/v1/models` | No documented limit | llmdeals §14 |
| Artificial Analysis | 24h | `/api/v2/language/models/free` | 100 req/day (free) | llmdeals §14, [AA docs][5] |
| models.dev | 24h | `/models.json` | No documented limit | llmdeals §14 |
| HuggingFace Router | 24h | `/v1/models` | No documented limit | PROVIDER-REFERENCE.md |
| OpenCode Go | 2h | Landing page + docs + data | N/A | llmdeals §15 |
| Nous Portal | 2h | Portal + blog | N/A | llmdeals §17 |
| Vercel Changelog | 2h | `/changelog` | N/A | llmdeals §21 |
| Hacker News | 2h | Firebase API (15 stories/list) | No documented limit | llmdeals §19, [HN API][3] |
| RSS Feeds | 2h | 8 provider blogs | N/A | llmdeals §18 |

**Daily API budget:** ~150-200 calls (well within AA free tier)

**Spec references:**
- [1]: https://dev.opencode.ai/go — OpenCode Go
- [2]: https://portal.nousresearch.com — Nous Portal
- [3]: https://github.com/HackerNews/API — HN Firebase API
- [4]: https://vercel.com/changelog/claude-sonnet-5-ai-gateway — Vercel changelog
- [5]: https://artificialanalysis.ai/data-api/docs — AA Data API docs
- [6]: https://openrouter.ai/docs/api/api-reference/models/get-models — OpenRouter models API
- [7]: https://pricepertoken.com — PricePerToken comparison
- [8]: https://github.com/mnfst/awesome-free-llm-apis — Awesome free LLM APIs
- [9]: https://github.com/icexun/ai-token-price — AI token price aggregator

## Agentic Usage

### For an agent deciding which model to use:

```bash
# "I need the cheapest model for a batch coding job"
curl localhost:8800/workload/coding_agent?limit=5

# "What's free and actually good?"
curl localhost:8800/categories/free?limit=5

# "I need vision + tool calling for under $1/M"
curl localhost:8800/deals/hot?limit=50 | jq '.deals[] | select(.input_per_m < 1 and .metadata.agentic_index > 50)'

# "How do I set up OpenRouter?"
curl localhost:8800/providers/openrouter/setup
```

### For monitoring deal changes:

```bash
# Check what's expiring in the next 4 hours
curl localhost:8800/deals/expiring?hours=4

# Check source health
curl localhost:8800/sources/health

# Get recent events
curl localhost:8800/events?limit=10
```

## Data Sources & Attribution

- **Artificial Analysis** — Intelligence index, benchmarks, performance (attribution required)
- **OpenRouter** — Model catalog, pricing, free variants
- **models.dev** — Model capabilities, modalities, benchmarks
- **HuggingFace Router** — Per-provider pricing, latency, throughput
- **OpenCode Go** — Provider-specific pricing and promotions
- **Nous Portal** — Model catalog and subscription plans
- **Hacker News** — Community deal signals
- **RSS Feeds** — Blog announcements and promotions

## Running as Cron

```bash
# Daily full poll (runs all sources)
cd /root/ass-rape-spunk-porn && python3 -m app.poll --all

# Due sources only (respects cadence)
python3 -m app.poll --due

# Single source
python3 -m app.poll --source openrouter-models
```

### Recommended Cron Schedule

```
# Full poll every 6 hours
0 */6 * * * cd /root/ass-rape-spunk-porn && python3 -m app.poll --all >> data/cron.log 2>&1

# Quick check every 2 hours (HN + RSS for new deals)
0 */2 * * * cd /root/ass-rape-spunk-porn && python3 -m app.poll --source hackernews --source rss-feeds >> data/cron.log 2>&1
```
