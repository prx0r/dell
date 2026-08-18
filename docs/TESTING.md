# Testing

## Test Suites

| Suite | Command | Result |
|-------|---------|--------|
| Proof Kernel | python3 -m app.invariant_tests | 14/14 PASS |
| Mutation | python3 -m app.mutation_tests | 10/10 (100%) |
| External Agent | python3 -m app.external_agent_tests | 10/10 PASS |
| Final Certificate | python3 -m app.certify_final | PASS |

## Test Categories

- Structural (DB, schema, imports)
- Truth (proof kernel, integrity)
- Decision (constraints, cost)
- Scoring (no priors, coverage)
- Mutation (kill rate)

## Source Adapter Tests

Each source adapter has `fetch()` and `extract()` functions that can be tested independently:

```python
from app.sources.free_llm_apis import fetch, extract
obs = fetch()
offers = extract(obs[0])
print(f"Offers: {len(offers)}")
```

## Verified Sources (42 total)

| Priority | Source | Cadence | Offers |
|----------|--------|---------|--------|
| 1 | opencode-go | 120min | models |
| 1 | nous-portal | 120min | models |
| 1 | awesome-free-llm-apis | 24h | 145 free tiers |
| 2 | litellm-prices | 24h | 3040 model prices |
| 2 | mcp-registry | 24h | 234 MCP tools |
| 2 | openrouter-models | 6h | models |
| 2 | hackernews | 2h | signals |
| 3 | models-dev | 24h | capabilities |
| 3 | context-engineering | 24h | patterns |
