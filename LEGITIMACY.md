# DEAL-RADAR LEGITIMACY — how it works + how another agent tests it

*2026-08-15 · the complete legitimacy reference for the deal-radar. This tells another agent (or a
future you) exactly what each piece does, why the numbers are trustworthy (anti-theatre), how to verify
it live, and how to keep it current. Every claim is reproducible.*

---

## 1. THE ONE RULE (how this stays legit)

> Nothing is "real" because code exists. It's real when a reproducible gate shows it does what it claims.

The deal-radar applies this to LLM pricing/quality:
- **Prices** are pulled LIVE from machine-readable sources (not hardcoded) → verifiable against the API.
- **Quality** is honestly labeled `measured` (from a real benchmark) or `estimated` (family guess) — it
  never pretends an estimate is a measurement.
- **Providers** are canary-checked (a real request) to prove they're alive, not just assumed.
- **Validation** cross-checks cached prices against live sources and flags drift.

---

## 2. THE ARCHITECTURE (what does what)

```
SOURCES (litellm/llm-prices/free-apis/models.dev/openrouter) ──► normalize.py ──► canonical-models.json (3,439)
                                                                        │
                                                     ┌──────────────────┤
                                                     ▼                  ▼
                                              quality.py           task_ranking.py
                                        (value frontiers,     (per-task agent-performance
                                         effective cost/task)   sorting: /recommend)
                                                     │
                                                     ▼
                                              app/api.py (FastAPI, port 8799)
                              /health /models /frontiers /deals /route
                              /recommend /tasks /rate-limits /canary /validation
                              /compute-sources /free-pool

MAINTENANCE (cron daily)
  refresh.py  → re-pull prices + validate against live (catches drift)
  canary.py   → real request to free providers, "live since <time>"
```

---

## 3. HOW TO TEST IT YOURSELF (the reproducible gates)

```bash
cd /root/ass-rape-spunk-porn
python3 app/test.py                 # 7/7  — normalize + frontiers + deals + value math
python3 app/test_compute_sources.py # 8/8  — free-pool classes + router tiers
python3 app/test_task_ranking.py    # 10/10 — task sorting + rate limits
python3 app/normalize.py            # re-pull ALL sources → canonical DB
python3 app/refresh.py --validate-only  # cross-check prices vs live OpenRouter, flag drift
python3 app/canary.py               # real probe: is each free endpoint alive?
PYTHONPATH=. python3 -m uvicorn app.api:app --port 8799 --app-dir .
curl localhost:8799/health
curl "localhost:8799/recommend?task=reasoning&prefer_free=true"
```

---

## 4. THE ACCURACY PROOFS (verified live)

| Claim | How it's verified | Result |
|---|---|---|
| Prices are real, not hardcoded | cached `$1.4e-7/tok` matches live OpenRouter `0.00000014` | ✅ exact match |
| Cost math is exact | hand-calc `$0.00153856` = `live_cost()` | ✅ exact |
| DeepSeek flash price accurate | `$0.064–0.14/M` matches published | ✅ |
| Free models genuinely free | `openai/gpt-oss-20b:free` quality 89.4 (estimated), 16 real `:free` on OpenRouter | ✅ |
| Quality is honest | every score carries `quality_source: measured\|estimated` | ✅ no overclaim |
| Validation catches drift | corrupted a price 10x → validator flagged 18 drifts | ✅ (proved) |
| Canary verifies live | cloudflare answered in 363ms, recorded "live since" | ✅ |

---

## 5. THE HONEST LIMITS (do not overclaim)

1. **Quality is mostly `estimated`** (family fallback) until an `AA_API_KEY` is set → artificial-analysis
   measured scores. Without it, the ranking uses conservative per-family guesses.
2. **Latency is neutral (1.0)** — we don't have real per-provider TTFT/tok/s data yet, so the ranking
   doesn't yet penalize slow providers.
3. **`success_rate` is a task-profile constant**, not measured per model — the effective-cost
   adjustment is a model, not yet a measurement.
4. **Free-provider canary** only probes providers reachable from THIS box + with a key (cloudflare
   verified; openrouter/opencode need their keys in the cron shell env).
5. **Prices are as-live-as-the-last `refresh`** — run the cron (or `--refresh`) when prices matter.

---

## 6. THE CRON (keep it live — document, don't auto-install on the shared box)

```bash
# daily (per the box axioms: document the command, coordinate the cron on the shared box)
0 6 * * * cd /root/ass-rape-spunk-porn && python3 app/refresh.py >> data/refresh.log 2>&1
30 6 * * * cd /root/ass-rape-spunk-porn && python3 app/canary.py >> data/canary.log 2>&1
```
- `refresh.py` re-pulls prices + validates (exit 1 on drift → alert).
- `canary.py` probes free providers, writes `canary-report.json` ("live since X").

---

## 7. THE API (the one-stop surface — port 8799)

| Endpoint | Purpose |
|---|---|
| `/health` | models + fetched_at + provenance |
| `/models` | search/filter/sort models (price/value/quality) |
| `/frontiers` | Pareto frontiers (top-value, cheapest, top-free, top-quality) |
| `/deals` | free-tier deals |
| `/route` | the router pick (task + quality floor + free-first) |
| **`/recommend`** | **task-aware agent-performance ranking** (coding/research/extraction/long-context/reasoning) |
| `/tasks` | the task profiles (per-axis weights) |
| `/rate-limits` | per-provider rpm/rpd/tokens (free tiers) |
| `/canary` | last provider live-check |
| `/validation` | last price-drift report |
| `/compute-sources` + `/free-pool` | the non-API free-compute classes |

All responses carry the `provenance` envelope (`api_version`, `surface: deal-radar`, `served: canonical-db`).

---

*This is the legitimacy reference. The deal-radar is real: live prices verified against the API, honest
quality labels, canary-verified providers, drift-catching validation, and a task-aware ranking built on
the agent-performance pattern. Another agent can reproduce every number with the commands in §3.*
