# LLM Deals — The Job-First Agentic Taxonomy

**The fundamental unit should not be: model → intelligence score → price**

**It should be: "I have this job. What is the cheapest model/provider/deal I can trust to do it?"**

This is much closer to how people actually talk about models.

---

## The vocabulary

### Frontage / Big Brain

*Give me the smartest thing available because this task is difficult enough that cost is secondary.*

Typical uses: architecture, difficult debugging, planning, novel reasoning, research synthesis, fixing something after cheaper models fail.

- Frontier = objective capability class
- Big Brain = recommended role

### Workhorse / Daily Driver

*Good enough + dependable + fast enough + cheap enough that I don't think about using it.*

This is the most important category. A workhorse isn't necessarily the smartest or cheapest.

Workhorse Score should NOT be just benchmark intelligence. Calculate:

```
Workhorse Score =
    task_success
  × reliability
  × instruction_following
  × agent_stability
  × speed
  × context_utility
  ÷ effective_task_cost
```

**Effective task cost, not token price.** Databricks found cheaper tokens did NOT necessarily mean cheaper coding tasks — one model used enough extra tokens that it ended up costing more per completed task despite cheaper token pricing.

**Don't rank $/million tokens. Rank $/successful task.**

### Fast / Flash / Mini

Vendors have converged on naming: Haiku, Flash, Mini, etc. Normalize to:

```
⚡ FAST
aka Flash / Haiku / Mini class
```

Ideal for: classification, extraction, summarization, formatting, simple code edits, search result processing, RAG workers, sub-agents, mass generation.

### Cheap Worker / Sub-agent

People describe architectures like:

```
Expensive smart model
        ↓
   makes the plan
        ↓
cheap cheap cheap
worker worker worker
        ↓
Frontier reviewer
```

Metrics differ from Frontier: cheap, fast, reliable tool calling, strict instruction following, low verbosity, low token burn, structured output, high concurrency, low failure rate.

### Agentic ≠ Intelligent

A model can write brilliant code in one response and be awful as an autonomous agent. Agentic ability needs separate measurements:

```
tool_call_accuracy
tool_selection
instruction_persistence
long_horizon_coherence
goal_completion
recovery_from_failure
verification_behavior
context_discipline
premature_completion_rate
loop_rate
tokens_to_completion
```

Intelligence: 91 / Agentic: 74 / Coding: 94 / Tool use: 63 is perfectly legitimate.

---

## The taxonomy (badges)

| Badge | What it means |
|-------|--------------|
| 🧠 **Big Brain** | Hardest problems |
| 🏆 **Frontier** | Current top capability class |
| 🐎 **Workhorse** | Best everyday price/capability/reliability |
| 🚗 **Daily Driver** | Model people realistically use constantly |
| ⚡ **Fast** | Low-latency interactive workloads |
| 🐜 **Worker** | Cheap repeated tasks/sub-agents |
| 🤖 **Agentic** | Reliable multi-step autonomous work |
| 🛠️ **Tool Caller** | Particularly reliable function/tool use |
| 💻 **Coder** | Software engineering |
| 🧭 **Planner** | Architecture/decomposition/reasoning |
| 🔍 **Reviewer** | Critique/testing/verifying another model |
| 📚 **Researcher** | Search + synthesis + sources |
| 📄 **Long Context** | Large repos/books/document sets |
| 🧲 **RAG** | Retrieval-grounded workloads |
| ✍️ **Writer** | Prose/style |
| 🎭 **Creative** | Storytelling/roleplay |
| 👁️ **Vision** | Image understanding |
| 🔒 **Private/Local** | Practical self-hosted option |
| 💎 **Hidden Gem** | Unusually good vs recognition/cost |
| 🥊 **Punches Above Weight** | Small/cheap relative to capability |
| 🆓 **Free** | Actually usable free inference |
| 🔥 **Hot Deal** | Exceptional temporary economics |

Don't use "Expert" — it's ambiguous with Mixture-of-Experts. Use "Specialist" instead: Specialist: Coding, Specialist: Translation, etc.

---

## What people actually want

### 1. Coding + agentic coding
"Cheapest models for agentic coding right now" — the first killer vertical.

### 2. "Good enough" models
Not #1 model. **Cheapest model that crosses my quality threshold.**

API: `GET /v1/recommend?task=coding&minimum_quality=80&sort=cheapest`

### 3. Cheap high-volume workers (swarm model)
For 100 sub-agents: $/task, tok/s, tool reliability, rate limits, concurrency, cached-input pricing, batch pricing.

### 4. Strong planner + cheap workers (stacks)
Support stacks, not just models:

```
BEST $10 AGENT STACK
  Planner: Frontier X
  Workers: Cheap Y
  Reviewer: Model Z
  Estimated: $0.18 / coding task
```

### 5. Tool calling reliability
OpenRouter exposes tool-calling popularity data. Expose: Tools supported, Parallel tool calls, Tool-call reliability %, Malformed calls %, Multi-turn tools, Agent loops.

### 6. Context that is actually usable
Distinguish: Advertised context, Effective tested context, Max economical context, Context price, Long-context quality degradation.

### 7. Local/private
Query by VRAM: `GET /v1/local?vram=24GB&task=coding&context=64k`

---

## The API

### Natural language endpoints

```
GET /v1/best/workhorse
GET /v1/best/big-brain
GET /v1/best/agentic
GET /v1/best/coding
GET /v1/best/subagent
GET /v1/best/tool-calling
GET /v1/best/research
GET /v1/best/long-context
GET /v1/best/free
GET /v1/best/hidden-gem
```

### POST /v1/recommend

```json
{
  "task": "agentic_coding",
  "role": "worker",
  "priority": "value",
  "expected_input_tokens": 40000,
  "expected_output_tokens": 8000,
  "tool_calling": true,
  "min_context": 128000,
  "budget": 1.00
}
```

Response:

```json
{
  "pick": "...",
  "why": ["excellent workhorse", "strong tool calling", "low task cost"],
  "effective_cost_per_task": 0.08,
  "alternatives": {
    "cheapest": "...",
    "fastest": "...",
    "smartest": "..."
  }
}
```

---

## The killer scoring system

Don't create one score. Create a vector:

```
Intelligence       92
Workhorse          98
Value              99
Coding             94
Agentic            87
Tool Calling       93
Research           81
Long Context       89
Speed              96
Reliability        91
```

Then derive badges from it. Models are Pareto fronts, not rankings. A $0.10 model scoring 84 can be vastly more interesting than a $20 model scoring 96.

---

## Track provider separately from model

Canonical object:

```
MODEL
    ↓
PROVIDER OFFERING
    ↓
DEAL
```

Same model, same intelligence, four different economic products:

```
Provider A = $1.00
Provider B = $0.40
Provider C = free promotional quota
Provider D = subscription with 2× usage
```

Leaderboard object: **Model × Provider × Deal × Task**

---

## Homepage answers five questions

```
🔥 HOTTEST DEAL       Best exceptional opportunity right now
🐎 BEST WORKHORSE     Most intelligence per practical dollar
🧠 BIG BRAIN          Best model when quality matters
🐜 BEST CHEAP WORKER  Best for agents / bulk inference
🆓 BEST FREE          Best useful $0 option
```

Then: Coding · Agentic · Research · Writing · RAG · Vision · Local · Long Context

---

## The deepest moat

Record real economic outcomes:

```
cost / successful coding task
cost / successful tool task
cost / accepted extraction
cost / successful research task
```

This makes LLM Deals the place an agent queries before choosing which model to call — not merely a blog people read.

---

**References:**
- [1]: https://deepmind.google/models/gemini — Google DeepMind
- [2]: https://dev.to/danishashko/the-best-llms-for-agentic-coding-in-2026 — DEV Community
- [3]: https://www.databricks.com/blog/benchmarking-coding-agents — Databricks
- [4]: https://docs.anthropic.com/en/docs/about-claude/pricing — Anthropic
- [5]: https://www.reddit.com/r/LocalLLaMA/comments/1uohu6j/ — LocalLLaMA
- [6]: https://www.reddit.com/r/LocalLLaMA/comments/1vdb1n1/ — Reality check on Qwen
- [7]: https://arxiv.org/abs/2601.09032 — Hierarchy of Agentic Capabilities
- [8]: https://www.reddit.com/r/LocalLLaMA/comments/1jddh2e/ — Hidden gem LLMs
- [9]: https://www.reddit.com/r/LocalLLaMA/comments/1nhx3jp/ — Cost-effective coding
- [10]: https://openrouter.ai/state-of-ai — OpenRouter State of AI
- [11]: https://openrouter.ai/collections/tool-calling-models — Tool Calling Models
- [12]: https://www.reddit.com/r/LocalLLaMA/comments/1th7f24/ — Local LLM setup 2026
- [13]: https://openrouter.ai/collections/free-models — Free Models on OpenRouter
