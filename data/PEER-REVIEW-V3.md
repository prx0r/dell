# Peer Review V3 — Production Readiness Audit

**Date:** 2026-08-18
**Verdict:** Pre-production intelligence platform, not yet production oracle

## Core Issue

> "The system can still produce authoritative-looking answers from state whose provenance, freshness, lifecycle, and uncertainty are not rigorously coupled to the answer being returned."

## P0 Issues

### 1. Verification schema/code inconsistency
- `get_verification_status()` queries `source_id FROM offers` but offers has no `source_id`
- Missing edge: Offer ← Claim ← Observation ← Artifact ← Source

### 2. Discovery attaches claims to wrong observation
- Uses `obs_ids[-1]` instead of current observation ID
- Corrupts evidence graph

### 3. Stale data can become immortal
- COALESCE(new NULL, old value) preserves stale facts
- Null cannot carry: VALUE_PRESENT, EXPLICITLY_ABSENT, NOT_OBSERVED, NOT_APPLICABLE, UNKNOWN, STALE

### 4. Poll failure does not invalidate truth
- Previous offers remain active when source fails
- Need: ACTIVE_VERIFIED, ACTIVE_UNVERIFIED, STALE, CONFLICTED, WITHDRAWN, EXPIRED, UNKNOWN

### 5. /v1/deals/live is weaker than name implies
- Verification levels are independent dimensions, not a ladder
- Need: pricing_claim, endpoint, model, inference, quota, promotion separately

### 6. Cryptographic proof is not actually immutable
- "sealed" is a label, not an invariant
- No DB trigger prevents modifications
- Test only checks status, not mutation resistance

### 7. Event-recorder bug
- Discovery passes source_id where offer_id required
- PK-10 should catch this but doesn't

### 8. Test rigor
- PK-06: 100K claims + 1 evidence = PASS (wrong)
- PK-07: evidence exists AND observation exists = PASS (wrong)
- PK-11: "from verification import" in file = PASS (wrong)
- PK-14: recipes >= 0 = PASS (impossible to fail)

## P1 Issues

### Scoring needs epistemic surgery
- Heuristics presented as measurements
- tool_calling=70 from boolean is misleading
- "agentic=90.8" not traceable to measurement

### Free qualification semantic errors
- requests_per_5h displayed as requests_per_day
- free=true means 12+ different things

### Model identity is next landmine
- MODEL != ENDPOINT != OFFER always
- Checkpoint ≠ quantization ≠ serving endpoint

### Too much parallel architecture
- 5 API files, 3 schema files, 8 scoring files
- Need: domain/, ingest/, evidence/, reconcile/, projections/, ranking/, api/

### API responses need epistemic metadata
- Every fact needs: value, state, source, observed_at, fresh_until, claim_id

### Freshness should be claim-specific
- Model author: permanent
- Context window: weeks/months
- List price: hours/day
- Flash promo: minutes/hours
- Availability: minutes

### Missing: conflict as first-class state
- Three different prices → CONFLICTED, not silent choice

### Missing: negative observations
- "I looked and it was not there" ≠ "I failed to find data"

### Missing: source authority by claim type
- OpenRouter authoritative for OpenRouter price, not for checkpoint details

### Missing: temporal validity as interval
- observed_at, valid_from, valid_until, superseded_at are different

## What's Excellent

- Claims separate from evidence
- Immutable source observations
- Verification checks
- Verification runs
- UNKNOWN semantics
- Endpoint-level modeling
- Quota policies
- Event history
- Source health
- Activation recipes
- Canonical model identity
- Provenance-aware design
- Gap reporting
- Free capacity planning
- Agent/MCP surface

## Production Readiness Scores

| Area | Score |
|------|-------|
| Product concept | 9/10 |
| Source breadth | 8/10 |
| Data modeling direction | 8/10 |
| Agent usefulness | 8/10 |
| Provenance architecture | 7/10 |
| Temporal correctness | 4/10 |
| Reconciliation/conflicts | 4/10 |
| Scoring epistemics | 4/10 |
| Verification rigor | 5/10 |
| Test rigor | 4/10 |
| Operational production readiness | 5/10 |
| Oracle credibility | 5/10 |

## ORACLE-1 Milestone

Seven invariants that must hold:
1. Every served factual field traces to ≥1 exact claim
2. Every claim traces to exact immutable observed bytes
3. No stale fact silently masquerades as current
4. Absence, unknown, stale, conflicted and false are distinct
5. No projection overwrites historical observation truth
6. "Verified" is multidimensional and claim-specific
7. Every production invariant has a test capable of genuinely failing

## Red Team II Tests

1. Stale deal attack
2. Conflicting source attack
3. Null poisoning
4. Observation provenance attack
5. Identity collision
6. Alias split
7. Quota semantics
8. Region conditionality
9. Parser degradation
10. Replay attack
11. Promotion leakage
12. Evidence mutation
13. Claim/evidence cardinality
14. Bad source authority
15. Canary ambiguity
16. Freshness decay
17. Clock error
18. Partial source outage
19. Duplicate canonical offer
20. Retraction
