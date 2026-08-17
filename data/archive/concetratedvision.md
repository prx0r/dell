# Concentrated Vision — The Canonical Live Data Layer

**The first product should be "the canonical live data layer for LLM inference economics", not another router.**

If you do that extremely well, routers, agents, IDEs, benchmarks, model selectors, newsletters, dashboards, research projects and procurement tools can all build on top of you.

## Core scope — four questions

1. What models/providers exist?
2. What do they cost right now?
3. What unusual deals/credits/free quotas/promos exist right now?
4. What is each option actually suitable for?

## The most important modeling decision

Keep these separate:

```
Model → ProviderOffering → CommercialOffer → DealEvent
```

Example:
- MiMo V2.5 (Model)
- OpenCode Zen / MiMo V2.5 (ProviderOffering)
- Zen PAYG (CommercialOffer)
- MiMo V2.5 Free (DealEvent)

## DealEvent — the object that matters most

Immutable-ish historical evidence. Never overwrite history.

```
DEAL DISCOVERED → DEAL VERIFIED → DEAL MODIFIED → DEAL EXPIRED → DEAL RESTORED
```

## API — boring and extremely useful

```
GET /v1/models
GET /v1/providers
GET /v1/offerings
GET /v1/deals
GET /v1/deals/live
GET /v1/deals/free
GET /v1/deals/expiring
GET /v1/prices
GET /v1/history
GET /v1/cheapest
GET /v1/best-value
GET /v1/free
GET /v1/promotions
```

Filters:
```
/v1/deals?task=coding&max_price=0.5&free=true&openai_compatible=true&automation_allowed=true&country=GB&min_context=128000
```

## Derived economics

```
nominal_input_cost, nominal_output_cost
effective_input_cost, effective_output_cost
batch_effective_cost, offpeak_effective_cost, subscription_effective_cost
free_quota_value, credit_value, deal_savings_percent
expected_cost_1k_requests, expected_cost_10m_tokens, expected_cost_agent_session
```

Presets: short-chat, coding-agent, RAG, bulk-extraction, translation, long-context-research

## Provenance — obsessive

Every value traceable:
```
value: 1500
source_id: source_xyz
source_type: official_docs
observed_at: ...
confidence: 1.0
```

Confidence levels: VERIFIED, LIKELY, COMMUNITY_REPORTED, UNVERIVERIFIED, EXPIRED

## Capability labels — soft data

Don't claim "Model X is the best workhorse." Expose evidence and derive versioned scores.

## Website — simple initially

Homepage: Hottest Deals, Best Free APIs, Best Workhorses, Cheapest, Fastest, Frontier, Recently Changed, Ending Soon, Newly Free, Price Drops

Deal page: status, verified timestamp, type, eligibility, sources, history, alternatives

Model page: all providers, cheapest, free, best deal, price history

Provider page: all models, limits, plans, promos, change history

## What NOT to build in V1

No: inference gateway, API-key vault, billing, resale, complicated router, agent framework, benchmarking platform, model hosting, chat UI

## Moat

> The highest-quality historical and real-time dataset of purchasable LLM inference opportunities.

Flywheel: more sources → more deals → more users → more corrections → better verification → better dataset → more integrations → more agents depend on API → providers submit deals → better coverage

## Mission (frozen)

> LLM Deals provides live, verifiable, machine-readable data about LLM models, providers, prices, free inference, promotions and availability.
