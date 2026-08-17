# Exact Implementation Order

Do not work in parallel on semantics that depend on one another.

## CP0 — Freeze + baseline

- record current head
- run all current tests
- save current dataset stats
- create final-hardening branch
- no ontology redesign

## CP1 — DecisionService

- create canonical RouteCandidate/RouteAssessment types
- move all hard constraints into one service
- exact cost/quota feasibility
- evidence policy
- endpoint-aware route identity
- rewrite `/resolve`

Acceptance:
RES-001..RES-020 pass.

## CP2 — Scoring V3

- remove provider-brand reliability priors
- split facts/measurements/quality/economics
- confidence separate from coverage
- task profiles
- workload-specific economics
- workhorse definition
- typed assessment object

Acceptance:
score mutation tests + missing-data tests pass.

## CP3 — Badge semantics

- typed badge input
- basis/evidence output
- factual/measured/quality/decision categories
- cohort-relative frontier if retained

Acceptance:
BADGE-001..012 pass.

## CP4 — MCP/REST convergence

- MCP calls shared services
- remove independent MCP recommendation
- exact parity suite
- remove NULL budget leak

Acceptance:
PAR-001..008 pass.

## CP5 — Free planner

- preserve quota window semantics
- remove invented defaults
- exact context feasibility
- exact token/request quotas
- free fraction/horizon

Acceptance:
quota mutation suite 100%.

## CP6 — Evidence depth

- field-level coverage report
- top 100 route prioritization
- activation fields
- current promotion fields

Acceptance:
top-100 critical field coverage target established and measured honestly.

## CP7 — Endpoint measurements

- endpoint probe correctness
- sample windows
- TTFT/TPS/success/tool/JSON
- no source-health substitution

Acceptance:
measured endpoint fields include sample count/time window.

## CP8 — Hermes skills

- consumer skills
- maintainer skills
- permission/termination contracts
- gap prioritizer

Acceptance:
autonomous run improves verified critical-field coverage without invariant violation.

## CP9 — Docs/repo convergence

- generated manifest
- generated API/MCP listings
- archive duplicate docs/engines
- executable README

Acceptance:
fresh clone follows README successfully.

## CP10 — Final certificate

Run `app.certify_final`.
Fix every FAIL.
No "PASS with caveat."

## CP11 — Live operations

24h live soak + backup/restore.
Publish live certificate separately.

## Stop condition

When CP10 deterministic certificate PASS and CP11 live certificate PASS, stop feature development and ship.
