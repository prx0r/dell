# Production Operations Final Gate

## CI

GitHub Actions must run from a clean checkout:

- lint/import check
- migrations on empty DB
- schema parity
- proof kernel
- unit/integration
- decision semantics
- REST black-box
- MCP black-box
- REST/MCP parity
- mutation
- docs/README execution
- package/container build

Critical checks block merge/release.

## Live operational certification

Separate deterministic CI from live-network tests.

Run and record:

- 24h collector soak
- endpoint probe schedule
- source 429/backoff behavior
- source outage recovery
- parser schema-drift fixture
- concurrent read/write
- scheduler overlap/idempotence
- process crash/restart
- disk/DB error handling
- backup
- restore
- corrupt-backup rejection

## Endpoint measurement

For top-value routes, collect:

- endpoint reachability
- inference success
- HTTP/provider error class
- TTFT
- output TPS
- tool success
- JSON/schema success
- model identity where observable

Record sample size and time window.

Do not convert one probe into a general reliability score.

## SLO-style summaries

For measured endpoints expose:

- sample count
- time window
- p50/p90 TTFT
- p50/p90 TPS
- success rate
- error distribution
- last successful inference
- last failed inference

No provider-brand priors.
