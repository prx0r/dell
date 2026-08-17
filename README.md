# LLM Deals

**The canonical live data layer for LLM inference economics.**

> LLM Deals provides live, verifiable, machine-readable data about LLM inference opportunities, with every important claim traceable to evidence and every uncertainty represented honestly.

## Quick Start

```bash
pip install -r requirements.txt
python3 -m app.cron_poll --all           # Poll 38 sources
python3 -m uvicorn app.api_canonical:app --port 8803  # Start API
python3 -m app.invariant_tests           # Run tests (10/10)
```

## 5 API Surfaces

| Port | API | Purpose |
|------|-----|---------|
| 8799 | V1 | Original (deprecated) |
| 8800 | V2 | Categories + providers |
| 8801 | V3 | Scoring + badges |
| 8802 | Hot | OpenAI-compatible router |
| 8803 | **Canonical** | **The data layer** |

## Canonical API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/models` | What models exist |
| `GET /v1/providers` | What providers exist |
| `GET /v1/deals` | Unusual opportunities |
| `GET /v1/deals/hot` | Active deals only |
| `GET /v1/free` | Free models ranked by utility |
| `GET /v1/catalog` | Everything (exhaustive) |
| `GET /v1/recommend` | Task-first recommendation |
| `GET /v1/mega-deals` | Institutional-quality deals |
| `GET /v1/verify/{model}` | Verify a specific deal |
| `GET /v1/probe` | Test if endpoints work |
| `GET /v1/stats` | Dataset statistics |
| `GET /v1/glossary` | All terms documented |

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

## Data

- **2396 offers** from 38 source adapters
- **599 free offers** with utility scoring
- **102 providers** with setup instructions
- **37 claims**, **131 events** in canonical DB
- **10/10 invariant tests** passing

## Identity System

```
EXACT_SAME_MODEL → can propagate benchmarks
SIBLING_VARIANT → cannot propagate benchmarks
SAME_MODEL_DIFFERENT_PROVIDER → may propagate context
```

## Scoring

10 dimensions: Intelligence, Workhorse, Value, Coding, Agentic, Tool Calling, Research, Long Context, Speed, Reliability

21 badges: Mega Deal, Frontier, Workhorse, Coder, Agentic, Fast, Hidden Gem, Free, Long Context, Tool Caller, etc.

## Tri-State Semantics

```python
price_state: FREE | PAID | UNKNOWN
automation_allowed: TRUE | FALSE | CONDITIONAL | UNKNOWN
region: NULL | country_code  # NULL = unknown, NOT "global"
```
