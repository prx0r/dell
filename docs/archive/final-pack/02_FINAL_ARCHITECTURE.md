# Final Canonical Architecture

Freeze the product around the following structure.

```text
SOURCES
  ↓
ARTIFACTS / OBSERVATIONS
  ↓
CLAIMS / ASSERTIONS
  ↓
RECONCILIATION + FRESHNESS + VERIFICATION
  ↓
CANONICAL ENTITIES
  MODEL
  ENDPOINT
  OFFER
  QUOTA
  CAPABILITY
  ↓
ROUTE VIEW
  model × endpoint × offer × region × time
  ↓
DECISION SERVICE
  hard constraints
  evidence policy
  workload economics
  task profile
  Pareto filtering
  preference ranking
  explanation
  ↓
┌──────────────┬──────────────┐
│ REST adapter │ MCP adapter  │
└──────────────┴──────────────┘
  ↓
HUMANS / AGENTS / ROUTERS
```

## Mandatory service boundary

Create or converge on:

`app/services/decision.py`

It owns:

- candidate construction
- hard constraints
- unknown/stale/conflict policy
- workload cost calculation
- quota feasibility
- route eligibility
- task quality profile
- ranking
- alternatives
- exclusion reasons
- decision confidence
- evidence coverage
- explanation

REST and MCP only validate inputs and serialize outputs.

## Canonical execution object

Do not rank a model alone.

```json
{
  "route_id": "...",
  "model_id": "...",
  "endpoint_id": "...",
  "provider_id": "...",
  "offer_id": "...",
  "region": "...",
  "quantization": "...",
  "as_of": "..."
}
```

A model may be good while one endpoint is unavailable, expensive, slow or tool-incompatible.

## Separation of concepts

Facts:
- price
- quota
- context
- tool support
- region
- retention policy
- availability

Measurements:
- TTFT
- TPS
- success rate
- tool success
- JSON success
- task benchmark

Derived metrics:
- workload cost
- free workload fraction
- empirical quality lower bound
- Pareto membership

Decisions:
- cheapest sufficient
- workhorse
- best free plan
- best cost/reliability route
- fallback route

Never place economics inside capability, popularity inside quality, or source-fetch health inside endpoint reliability.
