# DEAL-RADAR — VISION + CHECKPOINTED ROADMAP + LEGITIMACY

*2026-08-16 · The single north-star for `dealradar`: the live LLM price + quality + recommendation service,
built for agents. Read this first. It ties together the canonical model DB, the tension/routing recommender,
the MCP/API/site surfaces, and the anti-theatre gate. Every checkpoint is falsifiable: DONE only when a
logged, tested artifact exists.*

---

## 1. THE GOAL (one sentence)

> **Aggregate all machine-readable LLM pricing + measured quality into ONE live, canonical model DB, and
> recommend the best model for a task with full reasoning — via MCP, API, and a lean site — so any agent
> can pick the right model for the right job, provably.**

## 2. THE CORE (what "the deal radar" is)

A **live, self-updating, agent-facing LLM model DB**:
- **Canonical model DB** (1,985+ models) — prices (live), free tiers, context, capabilities, benchmarks,
  rate limits — from litellm + models.dev + OpenRouter + llm-prices + free-apis.
- **The recommender** — a multi-dimensional **tension engine** (9 tensions × 6 profiles) + **arXiv utility
  routing** (Phase-1 argmax / Phase-2 LinUCB) + **rate-limit awareness** (free ≠ good if too limited).
- **The three surfaces** — MCP (6 goal-oriented tools), HTTP API (16 endpoints, compact+ETag+provenance),
  lean Astro site (0-JS, JSON-LD).

## 3. THE MOAT (what makes it better than "just a price list")

1. **Measured quality, not marketing** — SWE-Bench/GPQA benchmark quality per task, `quality_source=measured`.
2. **Multi-dim utility** — the tension engine scores each model across 9 axes × 6 profiles (interactive /
   batch / quality / self-host / cheap / balanced), not just price.
3. **Rate-limit-aware** — a rate-limited free model ranks below a paid model that handles batch volume.
4. **LLM-reasoning** — the MCP returns the algorithm's FULL reasoning (tension scores + profile + utility +
   value + reason), so an agent gets decision-ready intelligence, not a black-box pick.
5. **Per-layer recommendation** — maps translation layers (T1/ARGMAP/L2/L200/C1) → task → model.

## 4. THE CHECKPOINTED ROADMAP (from DEV-PLAN; each = a falsifiable gate)

### ✅ DONE (65 tests pass)
- [x] Canonical model DB (1,985+ models) — `normalize.py`
- [x] Live prices + drift validation — `refresh.py`
- [x] Provider canary — `canary.py`
- [x] Measured benchmark quality — `benchmark_quality.py`
- [x] Tension engine (9×6) — `tensions.py`
- [x] Rate-limit-aware routing — `routing.py` + `free_limits.py`
- [x] arXiv algorithms (argmax + LinUCB) — `routing.py`
- [x] Per-layer recommendation — `layer_recommend.py`
- [x] API (16 endpoints) + MCP (6 tools) + lean site — `app/api.py`, `mcp/server.py`, `web/`

### ⬜ P1 — ingest the Tier-1 providers (the biggest gap)
- [ ] `_from_hf_router()` in `normalize.py` (HF Inference Providers: free tier + per-provider pricing)
- [ ] Add AkashML, Together, Mistral, DeepInfra, Fireworks, Gemini to `rate_limits.FREE_QUOTAS` + canary probes
- [ ] **Gate:** normalize count grows; a HF-router model has a real price; canary verifies it's live.

### ⬜ P2 — wire the LLM-reasons model (the moat)
- [ ] MCP returns the FULL reasoning (tension scores + profile + utility + value + reason)
- [ ] Expose `recommend_for_query` + `get_model_details` as the primary MCP tools
- [ ] **Gate:** MCP returns tension scores per pick; the output is decision-ready.

### ⬜ P3 — merge the tension engine + the arXiv routing
- [ ] `routing.recommend` accepts a `profile` and uses `tensions.PROFILES[profile]` as the weights
- [ ] **Gate:** batch→cost/rate-limit heavy; interactive→quality/latency heavy; self-host→open-weights.

### ⬜ P4 — per-layer translation integration (doc for the other agent)
- [ ] Write the integration doc in smellycock so workers auto-load `/layer-config` (HERMES_MODEL per layer)
- [ ] **Gate:** the doc is registered + the layer-config is correct.

### ⬜ P5 — hardening + deployment
- [ ] cron (refresh + canary daily)
- [ ] deploy API + Astro site (Cloudflare Worker/pages)
- [ ] wire the MCP into the Hermes profile
- [ ] **Gate:** cron runs, site serves, MCP callable from Hermes.

## 5. THE LEGITIMACY GATE (the ONE RULE, made executable)

> **Nothing is "real" because a model is listed. It is real only when (a) a logged test passes on the real
> data, (b) the price/quality resolves to a verified source, and (c) the number is machine-computed, not
> asserted.**

- Every model's price resolves to a real provider (PROVIDER-REFERENCE.md).
- Every benchmark is `quality_source=measured`, not marketing.
- The **anti-theatre audit** recomputes on fixed data and fails on mismatch (see `agent/audit.py`).
- A result with no content-addressed run record is flagged as theater.

## 6. THE NON-GOALS (honest)
- Don't add Bittensor/Kaito/io.net/Vast/Salad (raw compute, not inference APIs).
- Don't over-build the web (one homepage is enough; MCP/API are the real interface).
- Don't fight the smellycock MANIFEST (the other agent's coordination file).

---

*This is the north star. P1 is the immediate real next step (the missing Tier-1 providers are the biggest
value). The legitimacy gate keeps every number honest. The hermes layer (kanban + watchdog + audit) keeps
it running autonomously.*
