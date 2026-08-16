# DEAL-RADAR — GOALS & CHECKPOINTS (the build path)

*2026-08-16 · The concrete, checkable goals toward `VISION.md`. Each item is falsifiable: DONE only when a
logged, tested artifact exists. Order: **P1 → P2 → P3 → P4 → P5**.*

---

## ✅ DONE (65 tests pass — verified)

- [x] Canonical model DB (1,985+ models) — `normalize.py`
- [x] Live prices + drift validation — `refresh.py`
- [x] Provider canary — `canary.py`
- [x] Measured benchmark quality — `benchmark_quality.py`
- [x] Tension engine (9 tensions × 6 profiles) — `tensions.py`
- [x] Rate-limit-aware routing — `routing.py` + `free_limits.py`
- [x] arXiv algorithms (Phase-1 argmax + Phase-2 LinUCB) — `routing.py`
- [x] Per-layer recommendation — `layer_recommend.py`
- [x] API (16 endpoints) + MCP (6 tools) + lean Astro site
- [x] The agent-run orchestration layer (`agent/run.py`, `agent/watchdog.py`, `agent/audit.py`)

## PHASE P1 — ingest the Tier-1 providers (the biggest gap)

- [ ] Extend `normalize.py` with `_from_hf_router()` (HF Inference Providers).
- [ ] Add AkashML, Together, Mistral, DeepInfra, Fireworks, Gemini to `rate_limits.FREE_QUOTAS` + canary.
- [ ] **Gate:** normalize count grows; a HF-router model has a real price; the canary verifies it's live.

## PHASE P2 — wire the LLM-reasons model (the moat)

- [ ] MCP returns the algorithm's FULL reasoning (tension scores + profile + utility + value + reason).
- [ ] Expose `recommend_for_query` + `get_model_details` as the primary MCP tools.
- [ ] **Gate:** MCP returns tension scores per pick; the LLM-facing output is decision-ready.

## PHASE P3 — merge the tension engine + the arXiv routing

- [ ] `routing.recommend` accepts a `profile` and uses `tensions.PROFILES[profile]` as the weights.
- [ ] **Gate:** batch→cost/rate-limit heavy; interactive→quality/latency heavy; self-host→open-weights.

## PHASE P4 — per-layer translation integration

- [ ] Write the integration doc in smellycock (workers auto-load `/layer-config`, HERMES_MODEL per layer).
- [ ] **Gate:** the doc is registered + the layer-config is correct.

## PHASE P5 — hardening + deployment

- [ ] cron (refresh + canary daily) via the hermes watchdog.
- [ ] deploy API + Astro site (Cloudflare Worker/pages).
- [ ] wire the MCP into the Hermes profile.
- [ ] **Gate:** cron runs, site serves, MCP callable from Hermes.

---

## THE NON-NEGOTIABLE RULES

- **No claim without a logged test passing on real data.** Run `python3 app/test.py` + the per-module tests.
- **Every price/quality resolves to a verified source** (PROVIDER-REFERENCE.md) — `quality_source=measured`.
- **Reuse, don't rebuild** (litellm, llm-prices, awesome-free-llm-apis are the sources, not reimplemented).
- **The anti-theatre audit** recomputes on fixed data and fails on mismatch (`agent/audit.py`).
- **Box rules:** 8GB/4-core; refresh/canary are live-network — run one at a time, background long runs.
- Build **P1 → P5** in order; never present a phase as done before its gate passes.
