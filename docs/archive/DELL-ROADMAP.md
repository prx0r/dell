# Dell Production Roadmap

**Mission:** Turn `prx0r/dell` into a reproducible, adversarially tested, production-grade inference-economics oracle for llmdeals.org, then stop.

## Milestones

```
D0  Reproducibility        → Clean DB bootstrap from migrations
D1  Oracle Evidence Kernel → Provenance chain works
D2  Temporal Truth         → Freshness/stale/conflict semantics
D3  Identity Semantics     → MODEL != ENDPOINT != OFFER
D4  Economic Semantics     → Free = price + quota + availability
D5  Discovery/Ingestion    → Adapter contract + fixtures
D6  Verification           → EndpointTruth + probes
D7  API Contract           → Frozen public API
D8  Ranking/Recommendation → Epistemically labeled scores
D9  Adversarial Suite      → 30 mutation tests
D10 Operations             → Unattended reliability
D11 Data Coverage          → What Dell actually knows
D12 Release Certificate    → Machine-readable proof
```

## Dependency Graph

```
D0 → D1 → D2 → D3 → D4 → D5 → D6 → D7 → D8 → D9 → D10 → D11 → D12
```

No parallel jumping. Truth first.

## Release-Blocking Invariants (25)

INV-01: Every served factual value can produce a proof path
INV-02: Every claim identifies its exact observation
INV-03: Every observation commits to exact source bytes
INV-04: Historical observations are immutable
INV-05: Historical assertions are not overwritten
INV-06: NULL does not ambiguously mean absence
INV-07: Stale does not mean current
INV-08: Source failure does not imply fact absence
INV-09: Explicit absence is represented
INV-10: Conflicting credible assertions become CONFLICTED
INV-11: MODEL != ENDPOINT != OFFER
INV-12: Provider != model author
INV-13: Unknown quantization stays UNKNOWN
INV-14: Free has an explicit economic mechanism
INV-15: Quotas retain exact unit/window/scope
INV-16: Promotions retain temporal bounds
INV-17: Verification is multidimensional
INV-18: Measured values are distinguished from estimates
INV-19: Source authority depends on claim type
INV-20: Every invariant has a negative test
INV-21: Every negative test has at least one mutation proving it fails
INV-22: A clean DB behaves identically to a historical DB
INV-23: Public API filters are never silently ignored
INV-24: No stale claim enters /deals/live
INV-25: Release certificate can be reproduced from Git SHA

## Test Pyramid (9 classes)

1. Unit
2. Property
3. Fixture/parser
4. Database invariant
5. Integration
6. API contract
7. Adversarial
8. Mutation
9. Live canary

## What "Finished Dell" Means

```
✓ discovers inference resources
✓ stores original evidence
✓ extracts traceable claims
✓ maintains temporal history
✓ reconciles conflicting sources
✓ distinguishes absence / unknown / stale
✓ models model/endpoints/offers correctly
✓ models exact economics + quotas
✓ continuously checks endpoints
✓ exposes machine-readable provenance
✓ ranks only from epistemically labeled inputs
✓ survives parser/source failures
✓ rebuilds from a clean checkout
✓ passes adversarial + mutation tests
✓ emits reproducible production certificates
✓ runs unattended with observable health
```
