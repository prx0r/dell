# DEAL-RADAR — HERMES MCP / API (how an agent drives the service)

*2026-08-16 · The machine interface an agent uses to drive dealradar: the MCP tools, the HTTP API, and the
agent orchestrator. A hermes agent calls dealradar to pick the best model for a task with full reasoning.*

---

## 1. THE MCP SERVER (`mcp/server.py`) — the primary interface

6 goal-oriented tools (fewer tools work better for agents):
```
pick_model(task, min_quality, prefer_free)   → best model for THIS task
check_live_prices()                          → price-health (canary + validation)
get_model_details(model, task)               → granular detail + measured benchmark quality
get_free_sources()                           → free-pool + rate limits
recommend_for_query(query)                   → analyze a natural-language query → profile → pick + reason
recommend_model_for_layer(layer)             → per translation-layer model (T1/ARGMAP/L2/L200/C1)
```
Uses MCP SDK v2. To wire into hermes: `hermes mcp add dealradar` (point at the MCP server).

## 2. THE HTTP API (FastAPI, port 8799) — `app/api.py`

```
/health /models /frontiers /deals /route /recommend /tasks /benchmarks
/rate-limits /canary /validation /compute-sources /free-pool /tensions /recommend-layer /layer-config /ask
```
Agent-optimized: `format=compact` (54% smaller), `ETag` + stale-while-revalidate, provenance envelope.

## 3. THE AGENT ORCHESTRATOR (`agent/run.py`) — the hermles call layer

| Call | What it does |
|---|---|
| `python3 agent/run.py --step validate` | run all tests (the gate) |
| `--step normalize` | rebuild the canonical model DB |
| `--step refresh` | check live prices + drift |
| `--step canary` | probe the free providers (live) |
| `--step recommend --task coding` | recommend the best model for a task |
| `--step report` | the canonical count + health |
| `--step watchdog` | refresh → canary → validate → report cycle |

## 4. THE RECIPES

### Recipe A — "pick the best model for a task"
```bash
cd /root/dealradar
python3 agent/run.py --step recommend --task coding --min-quality 0.5
# or via MCP: pick_model(task="coding", min_quality=0.5)
```

### Recipe B — "check the service is healthy"
```bash
cd /root/dealradar
python3 agent/run.py --step report     # canonical model count + free-tier count
python3 agent/run.py --step canary     # are the free providers actually live?
python3 agent/audit.py --bench suite   # does the test suite reproduce on fixed data?
```

### Recipe C — "finish P1 (add Tier-1 providers)"
```bash
cd /root/dealradar
hermes kanban claim t_27d57d9f          # claim P1
# ... extend normalize.py with _from_hf_router() ...
python3 agent/run.py --step normalize   # count grows
python3 agent/run.py --step canary      # a HF-router model verifies live
python3 agent/audit.py --bench suite --record   # freeze the new golden
hermes kanban complete t_27d57d9f
```

### Recipe D — "audit for theater"
```bash
cd /root/dealradar
python3 agent/audit.py --list                    # every result has a content-addressed run
python3 agent/audit.py --bench suite             # recompute on fixed data; must match golden
```
> Any number with no run record / failing the golden audit is flagged as theater.

## 5. THE HONEST RULES

1. **No claim without a logged test passing on real data.** Use `agent/run.py --step validate`.
2. **Every price/quality resolves to a verified source** — `quality_source=measured`, never marketing.
3. **Anti-circularity:** the scorer ≠ the generator; the audit recomputes deterministically.
4. **Box rules:** refresh/canary hit the network — one at a time, background long runs, ~2GB free.
5. **Reuse, don't rebuild** (litellm, llm-prices, awesome-free-llm-apis are the sources).

---

## 6. THE MECHANISMS (from `research/AGENTIC-SCIENCE-MECHANISMS.md`)

| Mechanism | In dealradar |
|---|---|
| Content-addressed run record | `app/run_recorder.py` |
| Golden-file audit | `agent/audit.py` |
| Nanopublication triples | `app/run_recorder.py` |
| git+deps auto-capture | `app/run_recorder.py` |
| Kanban + cron watchdog | `sanskritbenchy`-style board + daily cron |
| Measured quality (not marketing) | `benchmark_quality.py` |
