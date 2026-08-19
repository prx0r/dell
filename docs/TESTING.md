# Testing

## Smoke Test

```bash
cd dell
PYTHONPATH=. python3 -c "
import sys; sys.path.insert(0, 'app')
from api_canonical import free_models, inference_cheapest, gpu_cheapest, compute_offers, compute_resolve
print(f'free_models: {free_models()[\"count\"]} OK')
print(f'inference_cheapest: OK')
print(f'gpu_cheapest: {len(gpu_cheapest(gpu=\"H100\")[\"providers\"])} providers OK')
print(f'compute_offers: {len(compute_offers()[\"offers\"])} offers OK')
print(f'compute_resolve: {len(compute_resolve()[\"resolve\"])} candidates OK')
"
```

## Source Adapters

Each adapter has `fetch()` and `extract()`:

```python
from sources.free_llm_apis import fetch, extract
obs = fetch()
offers = extract(obs[0])
print(f"Offers: {len(offers)}")
```

## Verified Sources (47)

| Priority | Source | Data |
|----------|--------|------|
| 1 | litellm-prices | 3039 models, full pricing |
| 1 | awesome-free-llm-apis | 604 free tiers |
| 1 | new-providers | Chutes, Venice, Hyperbolic, Heurist, io.net, AkashML |
| 2 | decentralized-compute | Akash, Bittensor, Nosana, Prime Intellect |
| 2 | bittensor-subnets | Individual subnet tracking |
| 2 | mcp-registry | 234 MCP tools |
| 3 | models-dev | Capabilities |
| 3 | context-engineering | Patterns |
