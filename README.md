# PĀṬALA DEAL RADAR — the live-updating LLM price + quality canonical resource

*2026-08-15 · a standalone app + API that aggregates all machine-readable LLM pricing/quality sources
into ONE canonical, live-updating model database, and answers "right now, what's the cheapest
sufficiently intelligent model for X?" — the llm-scavenger concept made real.*

---

## WHAT IT IS
Instead of a static spreadsheet, this is a **live radar**:
- **Ingests** every machine-readable LLM source into one normalized DB (3,439 models).
- **Scores** by **effective cost per successful task** (not $/M tokens) — a model that needs 3 attempts
  costs more.
- **Derives frontiers**: top value / cheapest / top free / highest quality / biggest free quota.
- **Answers the router query**: `route(task, min_quality, prefer_free)` → the top model right now.

## THE DATA STACK
| Source | Gives | Status |
|---|---|---|
| LiteLLM pricing DB | 3,040 provider/model combos | ✅ local clone |
| simonw/llm-prices | current + historical prices | ✅ local clone |
| awesome-free-llm-apis | free tiers + rate limits | ✅ local clone |
| models.dev | live catalog | ✅ live API |
| OpenRouter | live models + prices | ✅ live API |
| artificial-analysis | coding/agentic/intelligence scores | ⏳ optional (AA_API_KEY) |

## THE VALUE MATH (the clever part)
```python
quality = coding*0.4 + agentic*0.3 + intelligence*0.3
cost_per_job = (in_tok*in_price + out_tok*out_price) / 1e6
effective_cost = cost_per_job / success_rate     # penalizes retry-needing models
value_score = quality / effective_cost           # the frontier we rank by
```

## THE API (port 8799)
```
GET /health                          models + fetched_at
GET /models?search=&provider=&sort=value|price|quality&free=&limit=
GET /frontiers?mode=chat|all         the Pareto frontiers
GET /deals                           free-tier + subsidy signals (624 free models)
GET /route?task=coding&min_quality=&prefer_free=&limit=   the router pick
POST /refresh                        re-pull all sources
```

## VERIFIED (7/7 PASS)
- **3,439 canonical models** from all sources
- **Top free**: `openai/gpt-oss-20b:free` (quality 89.4), `nvidia/nemotron-3.5-lightning:free` (73.0)
- **Route** with floor 70 + free-first → qwen2.5-coder-3b, gpt-oss-20b
- **Quality floor is honest**: floor 95 → no model (max ~89), fail-closed
- **Effective-cost penalizes retry-needing models**

## RUN IT
```bash
cd /root/dealradar
python3 app/normalize.py                  # ingest all sources → data/canonical-models.json
PYTHONPATH=. python3 -m uvicorn app.api:app --port 8799 --app-dir /root/dealradar  # serve
```

## THE ROUTER INTEGRATION
This is the canonical price/quality source the `model_router.py` (in patalacheckpoints) queries before
a large job — instead of hardcoded tiers, the router asks `/route` and moves workloads onto whatever is
cheapest today.

## POLL CADENCE (the live-updating part)
- Structured catalogs (models.dev, openrouter, litellm): every **6h**
- Promos/changelogs (free-apis, llm-prices): **hourly–daily**
- Real API canary on important providers: **1-2×/day** to verify advertised endpoints work

*This is the standalone canonical resource. It aggregates, normalizes, scores, and fronts the LLM
landscape live — so the project's model choice is always current, cost-aware, and quality-gated.*
