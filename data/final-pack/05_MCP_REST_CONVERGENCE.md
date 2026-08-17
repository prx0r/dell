# REST/MCP Convergence

## Required architecture

```text
Pydantic/Input Schema
      ↓
DecisionService / QueryService / EvidenceService
      ↓
┌─────────────┬─────────────┐
│ FastAPI     │ MCP SDK     │
└─────────────┴─────────────┘
```

## Forbidden

- independent MCP recommendation scoring
- independent REST recommendation scoring
- independent NULL handling
- snapshot JSON as MCP truth
- duplicated badge rules
- duplicated provider filters

## MCP tools for external consumers

Keep the surface small and goal-oriented:

1. `resolve_inference`
2. `search_routes`
3. `compare_routes`
4. `explain_route`
5. `get_deal_changes`
6. `get_provider_setup`
7. `get_dataset_stats`

Optional:
8. `plan_free_workload`

Do not expose separate "recommend_model" logic. It should be a preset around `resolve_inference`.

## Exact parity tests

For the same request, REST and MCP must agree on:

- selected route_id
- model_id
- endpoint_id
- provider_id
- offer_id
- estimated cost
- hard exclusions
- evidence confidence
- freshness state
- badge/decision labels
- evidence IDs

Serialization differences are allowed. Semantic differences are not.

## Current issues to remove

In inspected `app/mcp_canonical.py`:

- max-price query allows NULL price through (`OR input_per_m IS NULL`);
- accepted `task` is not actually used in deal selection;
- recommendation logic is an independent simple scorer;
- MCP therefore remains vulnerable to drift despite using the canonical DB.

Replace those handlers with calls to shared services.
