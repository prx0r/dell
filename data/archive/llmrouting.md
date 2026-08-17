# LLM Routing — The Hot Router

**The site tells you where inference is cheap. The router acts on that information automatically.**

> "Give me the best acceptable answer while spending as close to $0 as possible."

## The product: Hot Router

```
models.dev
    +
LLM Deals live offers/promos
    +
user's API keys + remaining quotas
    +
task/capability scores
    +
live latency/reliability
    ↓
HOT ROUTER
    ↓
best provider/model for this exact call
```

LiteLLM as data plane (OpenAI-compatible gateway, retries, cooldowns, fallbacks).
But don't make LiteLLM's router your intelligence. Make it the executor underneath YOUR policy engine.

## Three routing decisions

### 1. Task router
coding, agentic coding, translation, extraction, research, reasoning, creative writing, tool calling, vision, summarization

### 2. Model router
Which models are capable + predicted success probability

### 3. Provider/deal router
Which provider/deal for that model based on quota, price, promotion, rate limit, TTFT, uptime

## Quota shadow pricing

Don't just do "free first." Maintain a shadow price for quota:

```
EXPECTED COST(model, provider, request) =
    actual marginal token cost
  + free_quota_shadow_cost
  + predicted_failure_probability × expected_escalation_cost
  + latency_penalty
  + reliability_penalty
  + context/token-burn penalty
```

If remaining quota is plentiful → shadow price ≈ $0 → burn them
If remaining quota is scarce → shadow price high → only route valuable/hard prompts
If credits expire tonight → shadow price collapses → BURN THEM NOW

## Cascading (FrugalGPT)

```
CheapModel
   ↓
confidence high → DONE
confidence low
   ↓
Workhorse
   ↓
still uncertain
   ↓
Frontier
```

## Step-level routing for agents

```
USER
 │
 ▼
Planner: 🧠 frontier/workhorse
 ├── search worker ─────── 🐜 free
 ├── grep worker ───────── 🐜 free
 ├── extraction worker ─── 🐜 cheap
 ├── coding worker ─────── 🐎 workhorse
 ├── formatting ────────── 🐜 cheapest
 │
 ▼
Reviewer: 🧠 strong
```

## Learn from every request

Collect outcome signals:
model chosen, task, tokens, latency, cost, fallback?, tool success?, agent completed?, user retried?, tests passed?, response accepted?

Update: P(success | model, task, context)

## The architecture

```
               LLM DEALS
                   │
      ┌────────────┴────────────┐
      │                         │
MODEL INTELLIGENCE       MARKET INTELLIGENCE
models.dev               promos
benchmarks               free tiers
community data           credits
your evals                prices
task scores               quotas
      │                         │
      └────────────┬────────────┘
                   │
             ROUTING ENGINE
                   │
        ┌──────────┼──────────┐
        │          │          │
      TASK       MODEL      OFFER
     ROUTER      ROUTER      ROUTER
        │          │          │
        └──────────┼──────────┘
                   │
              POLICY ENGINE
                   │
          quality / $ / speed
                   │
              LiteLLM/Bifrost
                   │
               providers
```

## The moat

Don't rebuild HTTP proxy, OpenAI compat, streaming, provider adapters, retry handling.

Build: DealGraph, QuotaLedger, TaskProfile, ModelCapabilityProfile, ProviderHealth, OutcomeHistory, RoutingPolicy

## The API

```json
POST /v1/chat/completions
model: "hot/workhorse"
```

Or:
```
model: "hot/free"
model: "hot/cheapest"
model: "hot/coding"
model: "hot/agentic"
model: "hot/frontier"
```

With policies:
```json
{
  "model": "hot/auto",
  "routing": {
    "quality_floor": 0.85,
    "max_cost_usd": 0.10,
    "prefer_free": true,
    "max_latency_ms": 5000,
    "allow_escalation": true
  }
}
```

## Research references

- RouteLLM: learned routers send simpler queries to cheaper models, 85% lower cost at 95% quality
- FrugalGPT: cascades match strongest model at 98% lower cost
- Hybrid LLM: configurable quality level, 40% fewer large-model calls
- MixLLM: contextual bandit + continual adaptation for changing model pools
- BaRP: online bandit for changing prices/workloads
- SeqRoute: multi-turn session budget management
- UCCI: confidence-calibrated escalation
- LLMRouterBench: 33 models, 21 datasets, 400K+ instances

## Research thesis

> Minimize expected cost per successful task under dynamic capability, latency, quota and market constraints.

---
**References:**
- [1]: https://docs.litellm.ai/docs/routing — LiteLLM Router
- [2]: https://models.dev — Models.dev
- [3]: https://github.com/lm-sys/routellm — RouteLLM
- [4]: https://arxiv.org/abs/2305.05176 — FrugalGPT
- [5]: https://arxiv.org/abs/2404.14618 — Hybrid LLM
- [6]: https://arxiv.org/abs/2502.18482 — MixLLM
- [7]: https://arxiv.org/abs/2510.07429 — BaRP
- [8]: https://github.com/aurelio-labs/semantic-router — Semantic Router
- [9]: https://github.com/ynulihao/LLMRouterBench — LLMRouterBench
- [10]: https://arxiv.org/abs/2605.18796 — UCCI
- [11]: https://arxiv.org/abs/2606.27457 — Cluster, Route, Escalate
- [12]: https://arxiv.org/html/2605.18859v1 — TwinRouterBench
- [13]: https://arxiv.org/html/2605.25424v1 — SeqRoute
- [14]: https://github.com/maximhq/bifrost — Bifrost
- [15]: https://github.com/spacepirate15/quantum-free-router — quantum-free-router
