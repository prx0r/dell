# API Reference

## Primary: POST /v1/resolve

```json
{
  "workload": {"task": "coding", "input_tokens": 2000, "output_tokens": 1000},
  "constraints": {"tools": "required", "context_tokens": {"min": 64000}},
  "preferences": {"optimize": "cost"},
  "evidence_policy": {"unknown": "exclude"}
}
```

## Other Endpoints

- GET /v1/routes
- GET /v1/models
- GET /v1/providers
- GET /v1/deals
- GET /v1/free
- GET /v1/workhorses
- GET /v1/high-value
- GET /v1/evidence/{id}
- GET /v1/coverage
