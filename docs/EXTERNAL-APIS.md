# External API Rate Limits & Documentation

## Artificial Analysis API

**Base URL:** `https://artificialanalysis.ai/api/v2`
**Auth:** `x-api-key` header
**Key:** stored in `.env` as `AA_API_KEY`

### Rate Limits
| Tier | Requests/24h | Window |
|------|-------------|--------|
| Free | 100 | Fixed 24h (not rolling) |
| Pro | 500 | Fixed 24h |
| Commercial | Custom | Contact AA |

**Key rules:**
- Window is fixed 24h, NOT rolling. First request after window ends starts new window.
- Quota resets when window ends, NOT by hour or per-request.
- Rate limit is shared across all API keys in an org/user scope.
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- On 429: check `Retry-After` header for seconds until reset.

### Endpoints We Use
| Endpoint | Tier | Cadence | Purpose |
|----------|------|---------|---------|
| `/language/models/free` | Free | 24h | All models with intelligence index, pricing, performance |
| `/language/models` | Pro | 24h | Full model data (if we get Pro) |
| `/language/models/{slug}` | Pro | on-demand | Single model detail |

### Response Shape (Free tier)
```json
{
  "tier": "free",
  "intelligence_index_version": 4.1,
  "pagination": {"page": 1, "page_size": 200, "total_pages": 2, "has_more": true},
  "data": [{
    "id": "...", "name": "...", "slug": "...",
    "release_date": "2025-08-05",
    "model_creator": {"id": "...", "name": "OpenAI"},
    "evaluations": {
      "artificial_analysis_intelligence_index": 24.5,
      "artificial_analysis_coding_index": 18.5,
      "artificial_analysis_agentic_index": 27.6
    },
    "pricing": {
      "price_1m_input_tokens": 0.06,
      "price_1m_output_tokens": 0.2,
      "price_1m_cache_hit_tokens": 0.015,
      "price_1m_cache_write_tokens": 0.075
    },
    "performance": {
      "median_output_tokens_per_second": 296.47,
      "median_time_to_first_token_seconds": 0.65,
      "median_end_to_end_response_time_seconds": 9.09
    }
  }]
}
```

### Attribution Requirement
> "When you display or share API data, credit Artificial Analysis as the source."

---

## OpenRouter API

**Base URL:** `https://openrouter.ai/api/v1`
**Auth:** None for model list (public)
**Docs:** `https://openrouter.ai/docs`

### Rate Limits
| Tier | Requests/min | Requests/day |
|------|-------------|--------------|
| Free (no key) | ~20 | ~200 |
| Free (with key) | 20 | 50 |
| Paid | Varies by model | Varies |

### Endpoint
`GET /models` — returns all available models with pricing, context, free variants.

---

## models.dev

**Base URL:** `https://models.dev`
**Auth:** None (public API)
**Docs:** `https://models.dev`

### Rate Limits
No documented rate limits. Poll conservatively (every 24h).

### Endpoint
`GET /models.json` — returns all models with modalities, capabilities, benchmarks, license.

---

## HuggingFace Router

**Base URL:** `https://router.huggingface.co`
**Auth:** None for model list
**Docs:** `https://huggingface.co/docs/inferenced/providers`

### Rate Limits
No documented rate limits for model list. Inference calls follow provider-specific limits.

### Endpoint
`GET /v1/models` — returns models with per-provider pricing, latency, throughput.

---

## Hacker News Firebase API

**Base URL:** `https://hacker-news.firebaseio.com/v0`
**Auth:** None (public)
**Docs:** `https://github.com/HackerNews/API`

### Rate Limits
No documented rate limits. Be polite (< 1 req/sec).

### Endpoints
- `GET /topstories.json` — top story IDs
- `GET /newstories.json` — new story IDs
- `GET /beststories.json` — best story IDs
- `GET /item/{id}.json` — single story/comment

---

## RSS Feeds

Standard RSS/Atom. No rate limits documented. Poll every 2h max.

---

## Polling Strategy

| Source | Cadence | Batch Size | Notes |
|--------|---------|-----------|-------|
| OpenRouter | 6h | 1 API call | Single endpoint, all models |
| models.dev | 24h | 1 API call | Single endpoint |
| AA (Free) | 24h | 2 calls (paginated) | 100 req/day limit — use wisely |
| HF Router | 24h | 1 API call | Single endpoint |
| OpenCode Go | 2h | 3 page fetches | HTML parsing |
| Nous Portal | 2h | 2 page fetches | HTML parsing |
| HN | 2h | ~90 API calls | 3 lists × 30 stories |
| RSS | 2h | N feeds | 1 call per feed |

**Total daily API calls (estimated):** ~150-200 (well within AA free tier)

## International Providers

Additional providers outside the US/EU are available via OpenRouter and HuggingFace Router, including:
- **DeepSeek** (China) — competitive pricing, strong coding models
- **Mistral** (France) — European provider, strong reasoning models
- **Alibaba/Qwen** (China) — via OpenRouter, competitive multimodal models
- **01.AI** (China) — via OpenRouter, Yi series models

These are accessible through the same API endpoints; no separate integration needed.
