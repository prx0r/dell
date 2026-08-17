# Final Peer Review

## Executive verdict

Dell is structurally close to finished, but the newest decision layer is not yet trustworthy enough to call final.

The evidence/identity/economics architecture should be frozen. The final work should focus on the consumer and agent-facing projection.

### Current strengths

- canonical SQLite truth layer
- explicit MODEL != ENDPOINT != OFFER identity
- economic access classes
- temporal/lifecycle semantics
- provenance and verification primitives
- claim-specific freshness work
- unknown-policy concept
- proof kernel restored to 14/14 in recent work
- canonical MCP direction
- unified `/v1/resolve` direction
- mutation testing and external utility testing
- useful public catalog/economics dataset

### Current critical weaknesses

#### P0 — `/resolve` is not yet a real resolver

`app/resolve.py` duplicates scoring rather than using the canonical scoring service.

Observed current behavior includes:

- `max_cost_usd` only rejects UNKNOWN price. It does not calculate workload cost and reject routes above the budget.
- task is effectively ignored by the scoring function.
- optimization preferences mostly multiply the same generic score instead of changing objective ordering.
- output price, request count, quota/capacity, availability, region, automation/KYC/card constraints and endpoint health are not part of the main decision.
- recommendation is offer-level, although the real unit of execution should be route = model × endpoint × offer.
- evidence policy is only partially applied.
- `decision.coverage` currently means fraction of offers surviving hard filters, not evidence coverage.
- alternatives do not carry full provider/route/reason/explanation metadata.

This endpoint is the right product abstraction, but its implementation must be replaced with a canonical DecisionService.

#### P0 — scoring V2 still contains semantic leakage

`app/scoring_v2.py` has improved structure, but:

- reliability falls back to provider/source-brand priors (`openrouter`/`opencode`) rather than endpoint observations;
- source reliability and inference endpoint reliability are conflated;
- `capability` starts from an invented baseline of 50;
- capability mixes tool support, context and FREE status;
- free status is economics, not capability;
- quality still falls back to raw cross-benchmark averaging/median;
- capacity normalizes incompatible quota windows into one arbitrary scale;
- throughput scaling is arbitrary and undocumented as a relative cohort;
- `_compute_confidence()` is effectively the same as coverage, so score is penalized twice by the same missing-data signal;
- route scoring accepts an endpoint object but most endpoint-specific measured state is not first-class.

#### P0 — badge engine and scoring output are structurally mismatched

Current badge predicates expect keys such as:

- `value`
- `workhorse`
- `throughput_tps`
- `ttft_ms`
- `tools_supported`
- `tools_success_rate`
- `coding_score`
- `agentic_score`

But `score_route()` emits dimensions named:

- `quality`
- `economics`
- `reliability`
- `throughput`
- `capacity`
- `capability`

Therefore several badge predicates cannot be satisfied from the structure they receive.

Fix by deriving badges from a typed Fact/Measurement/Decision object, not from loosely shaped dicts.

#### P0 — MCP still has decision semantics separate from REST

`app/mcp_canonical.py` correctly uses canonical SQLite, but it still implements independent query/recommendation logic.

Examples:

- max-price SQL explicitly allows `input_per_m IS NULL`;
- `task` is accepted but not used in `find_inference_deals`;
- `recommend_model()` uses a separate simple score;
- recommendation should call the exact same DecisionService used by `/v1/resolve`.

The rule must be:

> REST and MCP are adapters over one domain service. They are never separate business-logic implementations.

#### P0 — AGENTS.md is stale while claiming to be truth

At inspected head, `AGENTS.md` still records an older SHA and old key-file references (`scoring.py`, old MCP references, older tool counts).

Dynamic project state must not be manually maintained in Markdown.

Generate state/version/tool/API documentation from code/schema/manifests.

## Final rating

Architecture: 9/10
Evidence/identity/economics: 8.5–9/10
Decision semantics: 6/10
MCP parity: 6/10
Scoring semantics: 6/10
External utility: 7.5/10
Documentation integrity: 6/10
Final-release readiness: ~7.5/10

No new major subsystem is needed. The repo needs semantic convergence.
