# LLM Deals — Agent Integration Guide

## Quick Start

```bash
# Register MCP
hermes mcp add llm-deals --command node --args /root/ass-rape-spunk-porn/mcp/server.mjs

# Or use REST API
curl localhost:8803/v1/deals/free?limit=5
```

## MCP Tools (9)

| Tool | Use When |
|------|----------|
| `find_inference_deals` | "Find cheap coding model" |
| `get_free_models` | "What's free?" |
| `get_providers` | "How do I set up X?" |
| `get_provider_setup` | "Walk me through setup" |
| `get_best_by_badge` | "Best workhorse/coder/agentic" |
| `recommend_model` | "Best model for my task" |
| `get_deal_changes` | "What changed today?" |
| `explain_deal` | "Tell me about this deal" |
| `get_dataset_stats` | "How big is the dataset?" |

## REST API (port 8803)

| Endpoint | Use When |
|----------|----------|
| `/v1/models` | What models exist |
| `/v1/deals` | Unusual opportunities |
| `/v1/deals/hot` | Active deals only |
| `/v1/free` | Free models ranked by utility |
| `/v1/catalog` | Everything (exhaustive) |
| `/v1/recommend` | Task-first recommendation |
| `/v1/mega-deals` | Institutional-quality deals |
| `/v1/verify/{model}` | Verify a specific deal |
| `/v1/probe` | Test if endpoints work |
| `/v1/glossary` | All terms documented |

## Canonical Data Model

```
Model → ProviderOffering → CommercialOffer → DealEvent
```

## Identity Resolution

```
EXACT_SAME_MODEL → can propagate benchmarks
SIBLING_VARIANT → cannot propagate benchmarks
SAME_MODEL_DIFFERENT_PROVIDER → may propagate context
```

## Scoring

10 dimensions: Intelligence, Workhorse, Value, Coding, Agentic, Tool Calling, Research, Long Context, Speed, Reliability

21 badges: Mega Deal, Frontier, Workhorse, Coder, Agentic, Fast, Hidden Gem, Free, Long Context, Tool Caller, etc.

## Deal Types

Only unusual opportunities:
- Temporary free
- Usage multiplier (2x+)
- High capacity (3x+ baseline)
- Price anomaly
- Signup credits
- Startup/research credits

Ordinary market-rate models are in /catalog, not /deals.

## Tri-State Semantics

```python
price_state: FREE | PAID | UNKNOWN  # not just True/False
automation_allowed: TRUE | FALSE | CONDITIONAL | UNKNOWN
```

## How to Test

```bash
# Run full pipeline
python3 -m app.cron_poll

# Run invariant tests
python3 -m app.invariant_tests

# Run Hermes test
hermes -z "Use llm-deals MCP to find cheapest coding model"
```
