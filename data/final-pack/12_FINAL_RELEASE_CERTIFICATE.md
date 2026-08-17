# `app.certify_final` Contract

Create a final certifier that can only PASS when Dell is genuinely releasable.

## Required gates

### Structural
- empty DB bootstrap
- all migrations
- schema check
- no active imports from deprecated scoring/categories/MCP paths

### Truth
- proof kernel 100%
- claim/evidence integrity
- no stale-as-current
- no unknown coercion
- field-level coverage report generated

### Decision
- all RES tests pass
- hard constraint violations = 0
- exact workload cost tests pass
- quota-window tests pass
- evidence-policy tests pass

### Scoring/badges
- badge semantic tests pass
- no source-brand reliability priors
- no free-status capability bonus
- missing data cannot improve score
- confidence != coverage implementation verified

### Interfaces
- REST black-box
- MCP black-box
- semantic parity
- OpenAPI schema
- MCP schemas

### Adversarial
- critical mutation kill = 100%
- overall mutation >=95%
- malformed input suite
- SQL/path/request abuse tests

### External utility
- >=20 realistic tasks
- hard constraint violation = 0
- unsupported assertion = 0
- stale leakage = 0
- evidence retrieval >=95%

### Reproducibility
- README clean-room run
- Docker/container build
- fresh checkout certificate
- CI checks green

### Operations
May be a separate `LIVE_PASS` certificate:
- 24h soak
- backup/restore
- source outage recovery
- scheduler overlap
- probe persistence

## Status vocabulary

Only:
- PASS
- FAIL
- PARTIAL
- BLOCKED
- SKIP

SKIP never contributes to PASS.

## Output

`data/tests/final/<run-id>/`

Files:
- run.json
- environment.json
- commands.log
- structural.jsonl
- truth.jsonl
- decision.jsonl
- scoring.jsonl
- rest.jsonl
- mcp.jsonl
- parity.jsonl
- mutation.jsonl
- external-agent.jsonl
- coverage.json
- operations.json
- failures.json
- FINAL-CERTIFICATE.md

## Public claim policy

Only after deterministic FINAL PASS:
"production-ready inference-economics data and decision API"

Only after LIVE PASS + sufficient top-route empirical coverage:
"verified live inference oracle"

Do not use the stronger phrase before then.
