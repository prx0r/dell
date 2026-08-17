# LLM Deals

**The canonical live data layer for LLM inference economics.**

> LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.

## Quick Start

```bash
pip install -r requirements.txt
python -m app.cron_poll --all     # Poll all 17 sources
python -m uvicorn app.api_canonical:app --port 8803  # Start API
```

## Architecture

```
Source Adapters → Canonical SQLite → DealService → REST + MCP + Site
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

## API (port 8803)

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/models` | What models exist |
| `GET /v1/providers` | What providers exist |
| `GET /v1/deals` | Unusual opportunities |
| `GET /v1/deals/hot` | Active deals |
| `GET /v1/free` | Free models ranked by utility |
| `GET /v1/catalog` | Everything (exhaustive) |
| `GET /v1/recommend` | Task-first recommendation |
| `GET /v1/stats` | Dataset statistics |
| `GET /v1/glossary` | Terms for agents |

## Sources (17 adapters)

| Source | Data |
|--------|------|
| OpenRouter | 414 models, prices, free tiers |
| models.dev | 349 models, benchmarks, capabilities |
| HuggingFace Router | 312 models, per-provider pricing |
| Artificial Analysis | 608 models, intelligence scores |
| OpenCode Go | 11 models, 30K+ req/5h capacity |
| Alibaba Bailian | 246 free per-model quotas |
| Vercel Changelog | Launch pricing |
| Hacker News | Community leads |
| RSS (8 blogs) | Deal announcements |
| SenseNova, Sakura, Scaleway, OVH, Z.AI, + more | Regional providers |

## MCP Tools (9)

| Tool | Purpose |
|------|---------|
| `find_inference_deals` | Search by task/price/free |
| `get_free_models` | Ranked free models |
| `get_providers` | Provider setup info |
| `get_provider_setup` | Step-by-step setup |
| `get_best_by_badge` | Category rankings |
| `recommend_model` | Task-first recommendation |
| `get_deal_changes` | Recent changes |
| `explain_deal` | Deal deep-dive |
| `get_dataset_stats` | Overview |

## Identity System

```text
EXACT_SAME_MODEL → can propagate benchmarks
SIBLING_VARIANT → cannot propagate benchmarks
SAME_MODEL_DIFFERENT_PROVIDER → may propagate context
```

## Scoring

10 dimensions: Intelligence, Workhorse, Value, Coding, Agentic, Tool Calling, Research, Long Context, Speed, Reliability

21 badges: Mega Deal, Frontier, Workhorse, Coder, Agentic, Fast, Hidden Gem, Free, Long Context, Tool Caller, etc.

## Testing

```bash
python -m app.invariant_tests  # 10/10 invariants
python -m app.cron_poll         # Full pipeline
```
