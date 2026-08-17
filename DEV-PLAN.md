# GARGLECUM DEV PLAN — finish it (verified state + the remaining build)

*2026-08-15 · the honest finish-the-project plan for garglecum (fka dealradar). What's DONE + verified, what's
left, in priority order. Every item is gated (test) + tied to the provider reference. Garglecum is the
model intelligence layer for OpenPāṭala's Translation Factory.*

---

## WHAT'S DONE + VERIFIED (65 tests pass)

| Capability | Module | Status |
|---|---|---|
| Canonical model DB (1985 models) | normalize.py | ✅ ingests litellm + models.dev + OpenRouter + llm-prices + free-apis |
| Live prices + drift validation | refresh.py | ✅ validates cached vs live, catches drift |
| Provider canary (live check) | canary.py | ✅ probes free providers, "live since X" |
| Measured benchmark quality | benchmark_quality.py | ✅ SWE-Bench/GPQA per task, quality_source=measured |
| Multi-dim tension engine | tensions.py | ✅ 9 tensions × 6 profiles (interactive/batch/quality/self-host/cheap/balanced) |
| Rate-limit-aware routing | routing.py + free_limits.py | ✅ free ≠ good if too limited (penalizes tiny quota) |
| arXiv algorithms | routing.py | ✅ Phase1 utility argmax (RouteProfile/BELLA) + Phase2 LinUCB (PILOT) |
| Per-layer recommendation | layer_recommend.py | ✅ maps translation layers → task → model |
| LLM-facing data structure | model_data.py | ✅ full records for LLM reasoning |
| Advanced NL query | advanced_query.py | ✅ profile inference (batch/interactive/daily-calls) |
| API (19 endpoints) | api.py | ✅ compact format, ETag, provenance |
| MCP server (11 tools) | mcp/server.py | ✅ goal-oriented tools |
| Lean Astro homepage | web/ | ✅ 0-JS, JSON-LD |

---

## WHAT'S LEFT (priority order)

### P1 — Add the viable Tier-1 providers (the biggest gap)
**Do:** ingest the real OpenAI-compatible providers from PROVIDER-REFERENCE.md — especially
`router.huggingface.co/v1` (HF Inference Providers: free tier + per-provider pricing metadata),
`api.akashml.com/v1` (cheapest open models), Together, Mistral, DeepInfra, Fireworks, Gemini.
**Why:** these are real, usable, and currently MISSING from the registry. HF router alone adds hundreds
of models + a machine-readable price source.
**How:** extend `normalize.py` with a `_from_hf_router()` (GET `/v1/models` → pricing/context) + add the
providers to `rate_limits.FREE_QUOTAS` + canary probes.
**Gate:** normalize count grows; a HF-router model has real price + the canary verifies it's live.

### P2 — Wire the LLM-reasons model (the moat)
**Do:** the MCP should return the algorithm's FULL reasoning (tension scores + profile + utility + value
+ reason), not just picks — so the LLM gets the granular intelligence AND can reason further.
**How:** `tensions.score_model` returns per-tension breakdown; `analyze` returns profile + picks + reason.
Expose `recommend_for_query` (analyze) + `get_model_details` (full tensions) as the primary MCP tools.
**Gate:** MCP returns tension scores per pick; the LLM-facing output is decision-ready.

### P3 — Merge the tension engine + the arXiv routing
**Do:** the tension engine (tensions.py) and the utility router (routing.py) should be ONE consistent
recommender — use the tension-profile weights inside the utility argmax, so batch/interactive/quality
profiles feed the routing directly.
**How:** have `routing.recommend` accept a `profile` and use `tensions.PROFILES[profile]` as the weights.
**Gate:** batch profile → rate-limit/cost-heavy; interactive → quality/latency-heavy; self-host →
open-weights.

### P4 — The per-layer translation integration (OpenPāṭala Factory)
**Do:** OpenPāṭala's Translation Factory consumes `/patala/layer-config` (HERMES_MODEL per layer).
Write the integration so the Factory workers auto-load the recommended model per layer (T1/L0/ARGMAP/L2/L200/C1).
**How:** expose `get_patala_layer_config` MCP tool + `/patala/layer-config` API endpoint. Document the
integration in `HERMES-MCP-API.md` so the Factory agent can call it.
**Gate:** the MCP tool returns correct model per layer; the Factory agent can fetch layer config.

### P5 — Hardening + deployment
**Do:** (a) the cron (refresh + canary daily), (b) deploy the API + Astro site (Cloudflare Worker/pages),
(c) wire the MCP into the Hermes profile.
**Gate:** cron runs, site serves, MCP callable from Hermes.

---

## THE CLEAN ARCHITECTURE (after P1–P5)

```
PROVIDERS (HF-router, AkashML, Together, OpenRouter, models.dev, free-apis, ...)
   │ normalize.py (live prices + rate limits + benchmarks + capabilities)
   ▼
canonical-models.json (rich records: price/free/ctx/modalities/capabilities/benchmarks/rate-limits)
   │
   ├─ tensions.py (9 tensions × 6 profiles) ── the moat (multi-dim utility)
   ├─ routing.py (utility argmax + LinUCB) ── the arXiv algorithms
   ├─ layer_recommend.py ── per translation-layer model
   └─ model_data.py ── full records for the LLM
   │
   ▼
API (/ask /recommend /recommend-layer /tensions /rate-limits ...)
MCP (pick_model / recommend_for_query / recommend_model_for_layer / get_model_details ...)
Astro homepage (0-JS, JSON-LD)
```

---

## THE NON-GOALS (honest)
- Don't add Bittensor/Kaito/io.net/Vast/Salad (raw compute / not inference APIs — exclude).
- Don't over-build the web (1 homepage is enough; MCP/API are the real interface).
- Don't fight the smellycock MANIFEST (it's the other agent's coordination file).

---

*This finishes the deal-radar: P1 adds the missing providers, P2-P3 make the LLM-reasoning moat
coherent, P4 integrates with the translation stack, P5 hardens + deploys. All gated, all honest.*
