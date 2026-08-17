# GARGLECUM — OpenPāṭala's model recommendation layer (fka deal-radar)

The model intelligence layer for OpenPāṭala's Translation Factory and agentic system. Aggregates all
machine-readable LLM pricing/quality into ONE canonical, live-updating model DB, and recommends the
best model for each translation layer (SOURCE→T1→L0→ARGMAP→L2→L200→C1) via **API, MCP, and a lean
static site** — optimized for agents (token-minimal, cached, measured).

**Part of the OpenPāṭala ecosystem** — see `/root/openpatalaproject` for the main product.
Garglecum provides the model intelligence; OpenPāṭala provides the scholarly graph.

## The agent-run layer (hermes-orchestrated)

Garglecum is now fully agent-runnable, like sanskritbenchy:
- **`VISION.md` / `GOALS.md`** — the goal + checkpointed roadmap (P1–P5), each a falsifiable gate.
- **`agent/run.py`** — the orchestrator (validate/normalize/refresh/canary/recommend/report/watchdog),
  logs every step to `data/agent-runs.jsonl`.
- **`agent/watchdog.py`** — the daily health/freshness cycle (cron `garglecum-daily-watchdog`, 04:30 UTC).
- **`agent/audit.py`** — the golden-file audit (the executable ONE RULE): recompute on fixed data, fail on
  mismatch. Every result is content-addressed via `app/run_recorder.py` (nanopublication triples).
- **`HERMES-MCP-API.md`** — how a hermes agent drives the service (MCP tools + recipes).
- **`skills/deal-radar/SKILL.md`** — the hermes driver skill (verified loads).
- **Kanban board** `dealradar` — P1–P5 tasks with dependency links.

## The three surfaces (agents are the primary users)

### 1. MCP server (the primary interface) — `mcp/server.py`
5 goal-oriented tools (perf doctrine: fewer tools work better for agents):
```
pick_model(task, min_quality, prefer_free)  → best model for THIS task (coding/research/extraction/long-context/reasoning)
check_live_prices()                          → price-health (canary + validation)
get_model_details(model, task)               → granular detail + measured benchmark quality
get_free_sources()                           → free-pool + rate limits
get_patala_layer_config(layer)              ← OpenPāṭala: best model for translation layer (T1/L0/ARGMAP/L2/C1)
```
Uses the MCP SDK v2 (MCPServer). Compact (token-minimal) by design.

### 2. HTTP API (FastAPI, port 8799) — `app/api.py`
```
/health /models /frontiers /deals /route
/recommend /tasks /benchmarks /rate-limits /canary /validation
/compute-sources /free-pool
/patala/layer-config  ← OpenPāṭala Factory integration
```
Agent-optimized: `format=compact` (54% smaller payloads), `ETag` + `Cache-Control: stale-while-revalidate`,
provenance envelope on every response.

### 3. Lean static site (Astro, 0-JS) — `web/`
One homepage with category sections (free/coding/reasoning/vision) + the MCP/API callout. SEO for
agents: JSON-LD structured data, canonical, robots. Build: `cd web && npx astro build`.

## The data (canonical, live)
- **3,439+ models** from litellm + llm-prices + models.dev + OpenRouter
- **modality/capability tags** (vision/audio/reasoning/tool_call) from models.dev
- **measured benchmarks** (SWE-Bench 1134 models, GPQA, Terminal-Bench) as quality_source=measured
- **rate limits** for free tiers + the free-pool compute sources

## The legitimacy (anti-theatre)
Prices pulled live + validated against the API (drift-catching). Quality labeled `measured` vs
`estimated` (never overclaimed). Providers canary-checked (live since X). All gates reproducible:
`app/test*.py` → 32 PASS.

## Run it
```bash
cd /root/dealradar
python3 app/normalize.py          # re-pull + merge all sources → canonical DB
python3 app/refresh.py            # daily: refresh + validate prices (exit 1 on drift)
python3 app/canary.py             # daily: verify free providers are alive
PYTHONPATH=. python3 -m uvicorn app.api:app --port 8799 --app-dir /root/dealradar   # API
PYTHONPATH=mcp:app python3 mcp/server.py                                             # MCP (stdio)
cd web && npx astro build         # the lean homepage
```

## OpenPāṭala integration

Garglecum serves OpenPāṭala's Translation Factory by providing per-layer model recommendations:

```bash
# Get the recommended model for a specific translation layer
curl localhost:8799/patala/layer-config?layer=L2

# MCP tool for agents
get_patala_layer_config(layer="T1")
```

Translation layers: `SOURCE → T1 → L0 → ARGMAP → L2 → L200 → C1`

Each layer has different quality/cost/latency requirements:
- **T1** (gloss): cheap, fast, bulk
- **L0** (literal): moderate quality
- **ARGMAP** (argument mapping): high quality, careful
- **L2** (literary): high quality, nuanced
- **L200** (scholarly): highest quality, expert-level
- **C1** (commentary): high quality, contextual
