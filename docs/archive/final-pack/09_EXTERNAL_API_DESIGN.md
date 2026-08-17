# Consumer and Agent API Final Touches

## Public surfaces

Primary:
- `POST /v1/resolve`
- `GET /v1/routes`
- `GET /v1/models`
- `GET /v1/providers`
- `GET /v1/deals`
- `GET /v1/changes`
- `GET /v1/evidence/{id}`
- `GET /v1/coverage`

Convenience presets:
- `GET /v1/free`
- `GET /v1/workhorses`
- `GET /v1/high-value`

Convenience endpoints must call the DecisionService, not implement rankings.

## Response envelope

Every decision-heavy response should expose:

```json
{
  "data": ...,
  "meta": {
    "as_of": "...",
    "method": "...",
    "method_version": "...",
    "dataset_version": "...",
    "evidence_coverage": 0.0,
    "confidence": 0.0
  }
}
```

## Reason codes

Use stable machine-readable codes plus optional text:

- `PRICE_UNKNOWN`
- `COST_EXCEEDS_BUDGET`
- `TOOLS_UNKNOWN`
- `TOOLS_NOT_SUPPORTED`
- `CONTEXT_UNKNOWN`
- `CONTEXT_INSUFFICIENT`
- `QUOTA_UNKNOWN`
- `QUOTA_INSUFFICIENT`
- `REGION_MISMATCH`
- `AUTOMATION_NOT_ALLOWED`
- `REQUIRES_CARD`
- `REQUIRES_PHONE`
- `REQUIRES_KYC`
- `STALE_REQUIRED_FIELD`
- `CONFLICTED_REQUIRED_FIELD`
- `ENDPOINT_UNAVAILABLE`
- `QUALITY_EVIDENCE_INSUFFICIENT`

## Agent ergonomics

Prefer structured enums over overloaded booleans.

Example:
`tools: required | forbidden | any`

Do not accept query parameters you do not enforce.

Contract test:
every documented filter must change eligibility on at least one fixture.

## Explainability

`explain_route` should return:
- selected route
- selected objectives
- every hard constraint
- which facts established satisfaction
- evidence IDs
- alternatives
- excluded candidates with reason codes
- uncertainties

This becomes the audit trail for an autonomous router.
