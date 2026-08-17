# Decision Service / Resolve V2

## Endpoint

`POST /v1/resolve`

## Request schema

```json
{
  "workload": {
    "task": "coding",
    "input_tokens_per_request": 12000,
    "output_tokens_per_request": 3000,
    "requests": 400,
    "concurrency": 2
  },
  "constraints": {
    "max_total_cost_usd": 5.0,
    "free_only": false,
    "context_tokens_min": 64000,
    "max_output_tokens_min": 3000,
    "tools": "required",
    "json_schema": "required",
    "streaming": "any",
    "openai_compatible": "any",
    "automation_allowed": "required",
    "requires_card": "forbidden",
    "requires_phone": "forbidden",
    "requires_kyc": "forbidden",
    "regions": ["global", "KH"],
    "quantization": ["any"]
  },
  "preferences": {
    "objectives": [
      {"name": "cost", "weight": 0.45},
      {"name": "reliability", "weight": 0.30},
      {"name": "throughput", "weight": 0.15},
      {"name": "quality", "weight": 0.10}
    ]
  },
  "evidence_policy": {
    "unknown_hard_constraint": "exclude",
    "stale": "exclude",
    "conflicted": "exclude",
    "minimum_confidence": 0.70,
    "minimum_evidence_coverage": 0.60
  }
}
```

## Processing order

1. Resolve canonical route candidates.
2. Apply identity validity.
3. Apply lifecycle/availability.
4. Apply hard feature/policy constraints.
5. Apply unknown/stale/conflict evidence policy.
6. Validate per-request context/output feasibility.
7. Calculate workload cost from both input and output prices.
8. Calculate quota feasibility using exact quota window semantics.
9. Calculate free fraction / completion horizon if relevant.
10. Attach task-specific quality evidence.
11. Construct Pareto frontier.
12. Rank only among eligible frontier candidates according to preferences.
13. Return recommendation, alternatives and excluded candidates with reason codes.

## Hard constraints must be hard

If max cost = $5:

`estimated_total_cost > 5` => `COST_EXCEEDS_BUDGET`

If tools are REQUIRED:

- FALSE => `TOOLS_NOT_SUPPORTED`
- UNKNOWN => `TOOLS_UNKNOWN` unless policy explicitly allows unknown

If context minimum = 64k:

- context = 32k => `CONTEXT_INSUFFICIENT`
- context unknown => `CONTEXT_UNKNOWN`

No soft score can override a hard failure.

## Cost calculation

For each request:

```text
input_cost = input_per_m × input_tokens / 1_000_000
output_cost = output_per_m × output_tokens / 1_000_000
request_cost = input_cost + output_cost
total_cost = request_cost × requests
```

If a required price component is unknown, total workload cost is UNKNOWN.

Do not treat missing output price as zero.

## Quota feasibility

Context window is a per-request constraint, never a daily capacity.

Quota must preserve dimensions:

- metric
- value
- unit
- window
- scope
- reset semantics
- conditions

Examples:
- 100 req/day
- 1000 req/5h rolling
- 1M tokens/day
- 20 req/minute

Never merge different windows into a fabricated "daily capacity" unless explicitly deriving with clearly stated assumptions.

## Response schema

```json
{
  "status": "RESOLVED",
  "recommended": {
    "route": {...},
    "workload": {
      "estimated_cost_usd": 1.72,
      "free_fraction": 0.0,
      "estimated_completion_window": null
    },
    "metrics": {...},
    "evidence": {
      "coverage": 0.92,
      "confidence": 0.87,
      "as_of": "...",
      "stale_fields": [],
      "unknown_fields": []
    },
    "reasons": [
      {"code": "LOW_COST_FRONTIER", "detail": "..."},
      {"code": "TOOLS_VERIFIED", "detail": "..."}
    ]
  },
  "alternatives": [...],
  "excluded_summary": {
    "TOOLS_UNKNOWN": 218,
    "CONTEXT_INSUFFICIENT": 403,
    "COST_EXCEEDS_BUDGET": 117
  },
  "decision": {
    "method": "pareto-v1",
    "candidate_count": 37,
    "evidence_coverage": 0.81,
    "decision_confidence": 0.84,
    "as_of": "..."
  }
}
```

Do not label surviving-candidate fraction as `coverage`.
