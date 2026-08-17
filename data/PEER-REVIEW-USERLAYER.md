I went through the current head, scoring/category logic, canonical API, MCP implementation, Hermes-facing docs, and the latest red-team work. The main conclusion is:

**Dell’s truth/data architecture is now considerably better than its consumer decision layer.** The next optimization pass should stop adding infrastructure concepts and aggressively simplify, unify, and make the public semantics mathematically defensible.

The biggest issues are surprisingly mundane: duplicated ranking systems, different data paths between REST and MCP, labels whose definitions do not mean what a user thinks they mean, accepted API parameters that are ignored, and some “helpful” defaults that turn unknown data into invented certainty.

Current head is `746996f`, with a new 12-case API/security red-team artifact. The tests cover malformed requests, injection-shaped inputs, concurrency and HTTP misuse, which is useful, although the commit-level claim that this proves the system “secure under adversarial conditions” is much broader than those 12 HTTP tests establish.

# The most important discovery: Dell currently has two different products inside it

There is a good one:

```text
CANONICAL TRUTH LAYER

observations
→ claims
→ evidence
→ offers
→ endpoints
→ quotas
→ freshness
→ verification
```

And there is a much shakier one:

```text
CONVENIENCE / RANKING LAYER

workhorse
frontier
agentic
hidden gem
mega deal
best value
best free
fast
recommend
```

I would **freeze the first one** and substantially redesign the second.

The good news is this is final-touch work, not another architectural rewrite.

---

# 1. “Workhorse” currently does not have a coherent meaning

You asked specifically about this, and this is probably the clearest example.

There are actually **two different implementations of “workhorse.”**

`scoring.py` defines it as the unweighted average of whatever dimensions happen to be available:

```text
intelligence
coding
cost
speed
context
reliability
tool calling
```

But `categories.py` independently defines:

```text
35% cost
25% capabilities
20% context
20% daily capacity
```

Those aren't two implementations of the same metric.

They're two different concepts with the same name.

That should be P0.

## What “workhorse” should mean

I'd define it operationally:

> **A workhorse is an economical, dependable model-route combination capable of sustaining broad, repetitive agent workloads without hitting a major quality, capability, context, throughput or quota bottleneck.**

Notice **model-route**, not model.

A model may be a fantastic workhorse through one provider and terrible through another because Dell's entire thesis already recognizes:

```text
model
≠
endpoint
≠
offer
```

So score:

```text
WorkhorseCandidate =
    Model
  × Endpoint
  × Offer
```

Then use **hard gates first**:

```text
availability sufficiently fresh
price known
minimum task-quality evidence
requested capabilities satisfied
quota known OR explicit unlimited/metered state
endpoint not known-degraded
```

Then score eligible routes on:

```text
quality breadth
cost per useful workload
endpoint reliability
sustained throughput
usable quota/capacity
context adequacy
capability coverage
```

Crucially, I would use a **geometric mean or bottleneck-aware score**, not an arithmetic mean.

Why?

A workhorse with:

```text
quality       95
cost          95
reliability   20
```

is not an 70/100 workhorse.

It is an unreliable workhorse.

Something approximately like:

```text
base =
quality_breadth^0.25
× economics^0.20
× reliability^0.20
× throughput^0.10
× capacity^0.15
× capability^0.10
```

with normalized values and hard minimums gives you the right intuition: **one catastrophic weakness hurts substantially**.

Then apply an evidence penalty:

```text
final_score =
base
× evidence_coverage
× confidence_factor
```

A poorly characterized model should not beat a thoroughly measured one merely because missing dimensions disappeared from the average.

---

# 2. Missing data currently helps some models

This is one of the subtle problems I'd normally expect to be overlooked.

In `scoring.py`, `workhorse` averages the dimensions that happen to exist.

Imagine:

```text
MODEL A
intelligence 80
cost         90

workhorse = 85
```

because everything else is unknown.

Versus:

```text
MODEL B
intelligence 80
cost         90
speed        65
context      75
reliability  90
tools        70

workhorse ≈ 78
```

Model A can win because **we know less about it**.

That's backwards.

Every composite should report:

```json
{
  "score": 78.2,
  "coverage": 0.86,
  "confidence": 0.81,
  "dimensions_observed": 6,
  "dimensions_required": 7
}
```

And missing mandatory dimensions either:

```text
make candidate ineligible
```

or:

```text
reduce confidence
```

depending on the query.

Never quietly remove them from the denominator.

---

# 3. Unknown tool calling being converted to `50` should go

Current workhorse logic does:

```python
tool_calling if known else 50
```

That's exactly the sort of convenient assumption Dell was built to avoid.

Unknown means:

```text
UNKNOWN
```

not:

```text
50/100
```

More seriously, the recommendation function currently does this when the user requires tool calling:

```text
accept tool_calling >= 60
OR
accept tool_calling == UNKNOWN
```

So:

> “I require tool calling”

can return a model whose tool support is unknown.

That's unsafe agent semantics.

There should be a query-level policy:

```yaml
unknown_policy: exclude
```

Default it to `exclude` for **hard constraints**.

Allow:

```yaml
unknown_policy: allow_with_warning
```

only when explicitly requested.

---

# 4. There is an outright Tool Caller badge bug

Current tool capability mapping is:

```text
tool_call = true → tool_calling = 70
```

But:

```text
Tool Caller badge requires >=75
```

So if tool capability only comes from the Boolean metadata path, a model that definitely supports tools still **cannot receive the Tool Caller badge**.

That's a very useful example of why badges need semantic tests.

More importantly, `tool_calling=true` and `tool_calling quality=70` are not equivalent statements anyway.

Split these:

```text
tools.supported:
TRUE | FALSE | UNKNOWN

tools.success_rate:
measured percentage

tools.benchmark_score:
task benchmark

tools.schema_compliance:
measured percentage
```

Then:

```text
Tool Capable
```

can be a factual badge.

And something like:

```text
Strong Tool Use
```

can require measured performance.

---

# 5. “Agentic” is currently far too loose

Current badge logic effectively allows:

```text
intelligence >= 65
+
tool capability >=60
```

to mean:

```text
AGENTIC
```

That's not enough.

Agentic competence means more than tool API availability.

At minimum I'd distinguish:

```text
AGENT READY
supports tools
structured output
reasonable context

AGENT BENCHMARKED
has actual agentic benchmark evidence

AGENT WORKHORSE
agent benchmark + reliability + economics + tools

AUTONOMOUS CODING
specific coding-agent evidence
```

OpenRouter itself now distinguishes task-oriented benchmark categories including `coding`, `intelligence`, and `agentic`, and its benchmark interface preserves source/citation metadata. ([GitHub][1])

That vocabulary is much closer to what Dell should do.

---

# 6. “Frontier” should probably not be an absolute `80`

Current definition:

```text
median benchmark score >=80
→ Frontier
```

There are two problems.

First, benchmark scores are heterogeneous.

An 80 on:

```text
benchmark A
```

does not necessarily mean the same thing as an 80 on:

```text
benchmark B
```

Second, **frontier is inherently relative**.

A sensible definition would be something like:

> model is within the top X% / statistical band of current best-performing models on a defined quality profile.

For example:

```text
frontier.general
frontier.coding
frontier.reasoning
frontier.agentic
```

based on normalized benchmark evidence.

Or simply stop using `frontier` until you can define it rigorously.

---

# 7. Median of arbitrary benchmarks is not “intelligence”

Current `intelligence` is:

```text
median(all benchmark scores)
```

I would remove that.

The problem isn't the median itself; it's assuming benchmark raw percentages are interchangeable.

Better:

```text
raw score
    ↓
benchmark-specific normalization
    ↓
relative percentile / normalized performance
    ↓
task-domain score
```

Then maintain:

```text
coding
reasoning
knowledge
math
agentic
instruction_following
multimodal
```

and only construct a `general_quality` score from explicitly weighted domain scores.

LLMRouterBench's 2026 results are a warning here: it finds significant model complementarity and shows that many sophisticated routers fail to reliably beat simple baselines. In other words, **model suitability is highly task-dependent**, not reducible to one universal “intelligence” number. ([ACL Anthology][2])

That's actually great for Dell.

It reinforces:

```text
don't rank universally
resolve from workload
```

---

# 8. “Hidden Gem” currently means “high value”

Current definition:

```text
value >=80
→ Hidden Gem
```

But nothing in the metric establishes **hiddenness**.

A hugely popular model could be labelled Hidden Gem.

Rename it:

```text
High Value
```

unless you eventually acquire adoption/attention data.

A true Hidden Gem could mean:

```text
quality/value percentile high
AND
usage/adoption/search attention percentile low
```

That could eventually consume StackGraph-style data.

---

# 9. “Mega Deal” doesn't yet prove a mega deal

Current condition is roughly:

```text
capacity_multiplier >= 3
OR
usage_multiplier >= 2
```

That can be a **Promotion Multiplier** badge.

But Mega Deal implies relative economic exceptionalism.

I'd derive it from:

```text
effective price / normal baseline price
capacity / normal baseline capacity
promotion duration
eligibility
quality
```

For example:

```text
savings >= 50%
OR capacity improvement >=3×
```

plus:

```text
source-backed
active
usable
```

And return:

```json
{
  "badge": "mega_deal",
  "basis": "71% lower effective price than 30d baseline",
  "baseline": 0.42,
  "current": 0.12
}
```

Now the badge is auditable.

---

# 10. “Fast” currently mixes two fundamentally different things

`scoring.py` uses either:

```text
throughput TPS
```

or:

```text
requests per 5h
```

to produce `speed`.

Those aren't the same dimension.

Requests/5h is **capacity/quota**.

TPS is **generation throughput**.

And neither is **latency**.

Split:

```text
latency.ttft
throughput.output_tps
capacity.requests_window
capacity.tokens_window
```

Current OpenRouter provider routing does essentially this separation: price, throughput, latency, supported parameters, quantization and availability are distinct routing dimensions; it also exposes percentile performance windows rather than a single generic “speed” value. ([OpenRouter][3])

Dell should mirror that conceptual cleanliness.

---

# 11. There's also a comment/code mismatch in the speed normalization

The code comment says approximately:

```text
100 tps = 50
500 tps = 100
```

but the implementation is:

```python
speed = min(100, tps / 5)
```

which gives:

```text
100 TPS → 20
500 TPS → 100
```

One of them is wrong.

This should be caught by semantic tests, not just code tests.

---

# 12. Price scoring is too arbitrary

Current cost normalization approximates:

```text
100 - blended_price * 8
```

and blends:

```text
80% input
20% output
```

That's not robust.

Different workloads can look like:

```text
chat:
heavy input, light output

code generation:
moderate input, heavy output

translation:
approximately balanced

summarization:
huge input, small output
```

You already have workload presets.

Use actual:

```text
estimated_cost(workload)
```

instead of a generic price score.

This would also eliminate a lot of magic numbers.

---

# 13. Categories.py should probably be deleted from the serving path

This file has several serious semantic problems.

For instance:

```python
in_m = o.get("input_per_m") or 0
```

means:

```text
UNKNOWN input price → $0
```

inside Workhorse scoring.

That violates one of Dell's foundational rules.

`best_free_tiers` also invents capacity:

```text
unknown capacity → 500
```

and creates a composite:

```text
requests/day × 1000 + tokens/day
```

That's dimensionally meaningless.

It's like ranking vehicles by:

```text
miles + gallons
```

It also imports capabilities from provider metadata and implicitly applies them to individual offers.

A provider supporting tools somewhere does not establish that:

```text
this specific model
on this endpoint
```

supports them.

So I'd do:

```text
categories.py → deprecated/archive
```

and make all categorization call one canonical ranking engine.

---

# 14. “Best Vision” isn't actually Best Vision

Current implementation filters providers that claim vision support and sorts by input token cost.

That's:

> Cheapest vision-capable offer.

Not:

> Best vision model.

Rename it, or add actual image-task benchmarks.

Same for:

```text
Best for Agents
```

which currently gives points for:

```text
free
cheap
batch API
```

alongside capability flags.

Cheapness is useful for agent economics.

It isn't agent capability.

---

# 15. The canonical API still accepts filters that it ignores

This is a release-blocking API problem.

`/v1/deals` accepts:

```text
task
automation_allowed
country
```

but those parameters are not actually applied in the inspected implementation.

That's especially bad for an autonomous caller.

An agent sees:

```http
?automation_allowed=true
```

and reasonably assumes the result satisfies it.

Dell silently ignores it.

**Never accept a constraint unless you enforce it.**

Delete unsupported parameters or implement them.

I'd add a contract invariant:

> Every documented query parameter must demonstrably alter eligibility on at least one fixture.

---

# 16. Boolean filters need three-state semantics too

For example, `openai_compatible` only meaningfully filters when passed `true`; asking for:

```text
openai_compatible=false
```

doesn't symmetrically select incompatible providers.

Similarly, `tool_calling=false` isn't treated as a first-class request.

I'd stop using optional booleans for rich semantics and use:

```text
required
forbidden
any
```

For agents this is much clearer.

---

# 17. `/v1/deals/live` uses the wrong freshness abstraction

Currently a verification check up to **7 days old** can qualify a deal as live.

But Dell already has claim-type TTLs.

Use them.

A seven-day threshold might be acceptable for:

```text
model author
context claim
```

but absurd for:

```text
endpoint availability
flash promotion
temporary free quota
```

So `live` must mean:

```text
all claims necessary for the "live" assertion are fresh
under their own freshness policy
```

not:

```text
some verification happened in the last week
```

---

# 18. The FreeCompute planner has a conceptual bug

This deserves attention because it's one of the products with immediate user value.

Current planner computes:

```python
max_requests_by_context = context_window // tokens_per_request
effective_rpd = min(rpd, max_requests_by_context)
```

But context window is a **per-request limit**.

It is not a daily token allowance.

A 128k context model handling 3.5k-token requests does not mean:

```text
36 requests/day
```

It means each individual request fits.

So it should be:

```text
if tokens_per_request > context_window:
    route ineligible
```

Then daily capacity derives from:

```text
request quota
token quota
rate limit
runtime throughput
```

independently.

---

# 19. FreeCompute currently only understands `requests_day`

The query explicitly reads quota rows where:

```text
metric = requests_day
```

That throws away the economics work you've already done around:

```text
rolling 5h
tokens/day
requests/minute
account-dependent conditions
subscription allowances
promotional windows
```

And missing quota defaults to:

```text
50 RPD
```

That's another invented fact.

Replace with:

```text
capacity = UNKNOWN
```

and perhaps:

```text
route usable but capacity cannot be guaranteed
```

---

# 20. `min_quality` in FreeCompute is currently cosmetic

The endpoint accepts:

```text
min_quality
```

but doesn't use it in the inspected planner.

This is exactly the kind of thing I mean by nitpicking the consumer contract.

If I ask:

```text
min_quality=0.9
```

and Dell ignores it, an agent can make a materially bad decision.

Either implement:

```text
quality lower bound >= threshold
```

or remove it until Knee/AgentSLA supplies real quality evidence.

---

# 21. `/v1/cheapest` isn't really “cheapest usable”

It calculates economic cost and treats a free offer as cost `0`.

But:

```text
free
```

can mean:

```text
1 request/day
account condition
limited promotion
subscription included
region restricted
```

So use two endpoints/concepts:

```text
/cheapest-price
```

pure economic price.

And:

```text
/resolve
```

usable workload-aware recommendation.

Don't make `/cheapest` imply fitness.

---

# 22. The biggest agent-facing architecture bug: MCP is not using the canonical DB

This is P0.

The canonical REST API says:

> canonical SQLite DB, no silent fallback.

But the MCP implementation independently loads:

```text
snapshots/*.json
```

So:

```text
REST
```

and:

```text
MCP
```

are **not projections of one truth**.

They're separate data paths.

That defeats the Oracle architecture.

Fix this immediately:

```text
          DecisionService
               │
      ┌────────┴─────────┐
      ▼                  ▼
     REST               MCP
```

Both should call the same Python service functions.

Not:

```text
REST → canonical DB

MCP → snapshot JSON
```

---

# 23. There are currently two MCP servers too

The repo has:

```text
mcp/server.py
mcp/server.mjs
```

plus `tool_runner.py`.

Unless there is a deliberate compatibility reason, choose one authoritative implementation.

The pattern of Dell's history is that duplicated implementations eventually diverge.

You've already archived old API versions for that reason.

Do the same here.

---

# 24. MCP's `max_price` has a classic NULL bug

Current MCP filtering does effectively:

```python
(input_per_m or 0) <= max_price
```

Therefore:

```text
price = UNKNOWN
```

becomes:

```text
price = $0
```

for filtering purposes.

That's severe because it can recommend unknown-price models under a strict budget.

Canonical rule:

```text
unknown hard-constraint field → ineligible by default
```

should be enforced in one shared resolver.

---

# 25. MCP `find_inference_deals(task=...)` ignores `task`

The schema advertises:

```text
task
```

but the handler filters free and max price only.

Again: misleading machine contract.

The solution isn't to add random task heuristics.

Have that tool call the same resolver as REST.

---

# 26. MCP badge ranking is wrong by construction

`get_best_by_badge` filters models possessing the requested badge and then sorts **all badges by Workhorse score**.

So:

```text
get_best_by_badge("fast")
```

doesn't rank primarily by speed.

And:

```text
get_best_by_badge("coder")
```

doesn't rank primarily by coding.

You want category-specific ordering:

```text
fast → throughput/latency objective
coder → coding score
value → workload cost-quality
workhorse → workhorse score
```

Better still, stop exposing badge ranking as a special tool and expose:

```text
resolve_models(objective, constraints)
```

---

# 27. The MCP taxonomy is already drifting

`AGENTS.md` says there are nine tools but its table shows eight names.

`README.md` says nine tools with a different set.

Actual Python MCP declares **ten** tools.

And `HERMES-MCP-API.md` describes **11 older tools**, older API ports, old concepts such as `pick_model`, and other pre-canonical infrastructure.

This is an organizational failure now, not just stale documentation.

An autonomous maintainer cannot know what contract is canonical.

I'd generate the MCP/API documentation **from schemas**, never by hand.

---

# 28. README is substantially stale too

README currently advertises:

```text
5 API surfaces
V1/V2/V3/Hot/Canonical
```

despite previous work archiving the legacy APIs. It also reports older counts and claims “21 badges,” while current `scoring.py` defines ten visible badge labels.

Meanwhile `AGENTS.md` says:

```text
AGENTS.md is the single source of truth
```

but its own Git SHA is `4abdd25`, several commits behind current head.

Don't make a Markdown file the source of truth for dynamic project state.

Instead generate:

```text
MANIFEST.json
```

from implementation/tests and derive docs from that.

---

# 29. I would replace the current consumer vocabulary with four layers

The cleanest final product taxonomy is:

### Facts

No judgment.

```text
price
quota
context
tools_supported
availability
TTFT
TPS
benchmark result
```

### Capabilities

Mostly factual:

```text
tool-capable
vision-capable
long-context-capable
JSON-capable
OpenAI-compatible
```

### Measurements

Empirical:

```text
fast
reliable
strong tool use
strong coding
high context effectiveness
```

### Decisions

User/workload dependent:

```text
best-value-for-X
workhorse-for-X
cheapest-sufficient-for-X
best-free-plan-for-X
```

This prevents:

```text
cheap
```

from being accidentally interpreted as:

```text
agentic
```

---

# 30. I'd actually simplify the public badges

Keep consumer-friendly badges, but make each one a projection of explainable facts.

I would ship approximately:

| Badge                   | Meaning                                         |
| ----------------------- | ----------------------------------------------- |
| **Free**                | zero-price/allowance mechanism explicitly known |
| **Promo**               | temporary economic improvement                  |
| **High Value**          | good quality/cost frontier for stated workload  |
| **Workhorse**           | broad sustained workload fitness                |
| **Fast Output**         | high measured TPS                               |
| **Low Latency**         | low measured TTFT                               |
| **Long Context**        | large advertised context                        |
| **Long-Context Proven** | measured long-context performance               |
| **Tool Capable**        | supports tools                                  |
| **Tool Proven**         | measured tool success                           |
| **Coding Strong**       | coding benchmark evidence                       |
| **Agent Strong**        | agentic benchmark evidence                      |
| **Frontier Coding**     | current relative frontier for coding            |
| **Frontier Reasoning**  | current relative frontier for reasoning         |

I would remove:

```text
Hidden Gem
Mega Deal
Agentic
Frontier
Fast
```

as unqualified labels unless accompanied by the more precise semantics above.

---

# 31. “Long Context” needs two meanings

Current context category is essentially advertised context size.

Keep:

```text
advertised_context_tokens
```

but separately establish:

```text
effective_context
long_context_quality
```

Research such as HELMET has specifically shown that synthetic context-window tests can poorly predict downstream long-context performance and that different long-context task families behave differently. ([arXiv][4])

So:

```text
1M Context
```

can be factual.

But:

```text
Best Long Context
```

needs evaluation.

---

# 32. The final API should revolve around `/resolve`

This would simplify almost everything.

Instead of users learning:

```text
/deals
/free
/cheapest
/best-value
/recommend
/mega-deals
/categories
```

give agents one serious decision primitive:

```http
POST /v1/resolve
```

Input:

```json
{
  "workload": {
    "task": "coding",
    "input_tokens": 12000,
    "output_tokens": 3000,
    "requests": 400
  },

  "constraints": {
    "tools": "required",
    "context_tokens": {
      "min": 64000
    },
    "max_cost_usd": 5,
    "free_only": false
  },

  "preferences": {
    "optimize": [
      "cost",
      "reliability",
      "throughput"
    ]
  },

  "evidence_policy": {
    "unknown": "exclude",
    "stale": "exclude",
    "minimum_confidence": 0.7
  }
}
```

Output:

```json
{
  "recommended": {...},

  "alternatives": [...],

  "excluded": [
    {
      "route": "...",
      "reason_codes": [
        "TOOLS_UNKNOWN"
      ]
    }
  ],

  "decision": {
    "method": "pareto_v1",
    "confidence": 0.86,
    "as_of": "...",
    "data_coverage": 0.91
  }
}
```

Then `/free`, `/workhorse`, etc. can just be presets over this resolver.

This is much closer to current routing systems, where hard constraints such as supported parameters, data policy, quantization and maximum price are separated from preference criteria such as throughput or latency. ([OpenRouter][3])

---

# 33. Do hard constraints before scores

This deserves to be a formal invariant.

Never:

```text
score everything
→ hope a model with no tools doesn't rank too highly
```

Always:

```text
candidate universe

→ identity resolution

→ hard capability constraints

→ economic constraints

→ policy constraints

→ freshness/evidence policy

→ candidate set

→ Pareto frontier

→ soft preference ranking
```

That's much easier to reason about and test.

---

# 34. Explanations should be first-class

For consumers:

> Why is this a Workhorse?

For agents:

```json
{
  "badge": "workhorse",
  "score": 82.1,

  "basis": {
    "coding_quality": {
      "value": 84,
      "kind": "MEASURED"
    },
    "effective_cost": {
      "value": 0.038,
      "unit": "usd/request",
      "kind": "DERIVED"
    },
    "endpoint_success": {
      "value": 0.991,
      "kind": "MEASURED"
    }
  }
}
```

A badge without its derivation shouldn't be in the Oracle response.

---

# 35. Add explicit standards-inspired constraints

There's no universal industry standard called “Workhorse” that Dell needs to copy.

But there are increasingly common routing concepts worth aligning with.

Current OpenRouter routing distinguishes:

```text
price
throughput
latency
parameter support
quantization
fallback policy
data collection
zero-data-retention
```

and uses recent outage/performance information when selecting providers. ([OpenRouter][3])

I would therefore normalize Dell constraints around concepts such as:

```text
supports_tools
supports_json_schema
supports_streaming
quantization
data_retention_policy
region
max_price
min_throughput
max_ttft
availability
```

Then Dell becomes easy to integrate into gateways without inventing idiosyncratic semantics.

---

# 36. Hermes needs real product skills, not just an operations document

I did not find repository-contained `SKILL.md` artifacts in the current review; what exists is primarily `agent/*.py`, operational documentation, and Hermes/MCP instructions. The `agent` directory currently contains audit, run, trace and watchdog scripts.

I'd formalize distinct Hermes skills.

This is the **one implementation list** I'd give the maintainer:

1. **`dell-query`** — read-only consumer skill. Uses only canonical REST/MCP. Never touches DB.
2. **`dell-resolve`** — turns a workload into hard constraints/preferences and calls `/resolve`.
3. **`dell-explain`** — follows recommendation → fields → claims → evidence.
4. **`dell-discover`** — finds candidate offers/sources but cannot canonically commit them.
5. **`dell-investigate`** — produces structured source observations/artifacts.
6. **`dell-reconcile`** — handles conflicting claims according to authority rules.
7. **`dell-verify`** — runs source/endpoint verification and stores dimensions.
8. **`dell-gap`** — selects the highest-value UNKNOWN/STALE facts for investigation.
9. **`dell-source-repair`** — diagnoses parser/source degradation without turning failures into absence.
10. **`dell-certify`** — executes deterministic, mutation, REST/MCP parity, utility and live tests; cannot modify implementation while grading.

Every skill should declare:

```text
inputs
outputs
permissions
allowed writes
termination condition
evidence artifacts
failure states
```

That is much better than one giant Hermes agent knowing “how Dell works.”

---

# 37. Separate consumer agent from maintainer agent

This will help enormously.

### Consumer mode

Can:

```text
search
resolve
compare
plan
explain
retrieve evidence
```

Cannot:

```text
poll
modify DB
reconcile
run migrations
```

### Maintainer mode

Can:

```text
discover
ingest
verify
repair source
reconcile
certify
```

This distinction should appear in the MCP server too.

Most external users should never see:

```text
internal source-management concepts
```

---

# 38. Certification should test semantics of every label

You now have mutation and red-team infrastructure, which is good. The latest HTTP red-team artifact is useful, but its cases mostly establish that requests don't produce obvious failures; they do not validate semantic decisions.

Add a **Badge Truth Suite**.

Examples:

```text
BADGE-WORKHORSE-01:
missing reliability must not outrank measured reliable candidate

BADGE-TOOL-01:
tool_call=true can produce Tool Capable

BADGE-TOOL-02:
tools unknown cannot satisfy tools=required

BADGE-FRONTIER-01:
frontier status changes when cohort improves

BADGE-HIDDEN-01:
high-value popular model must not be called hidden

BADGE-FAST-01:
RPD cannot affect TPS label

BADGE-LONG-01:
advertised context cannot imply long-context quality

BADGE-FREE-01:
unknown price cannot become free

BADGE-MEGA-01:
expired multiplier cannot remain mega
```

These are much more valuable now than more SQL schema tests.

---

# 39. The source-health/reliability distinction still needs scrutiny

Recent commit `a95fe4f` claims:

```text
520 offers have measured reliability
no placeholder baselines
```

but it simultaneously reports only **12/14 proof-kernel tests passing**, including failures in core claim/evidence invariants.

Also, the current `scoring.py` content I fetched still contains a fixed provider reliability baseline of `70/50`.

So either:

```text
current scoring.py wasn't fully wired
```

or:

```text
the commit message overstates the change
```

That needs immediate reconciliation.

And even when it is wired:

```text
source_health
```

is not necessarily:

```text
inference endpoint reliability
```

A provider's pricing-page collector succeeding 99% of the time says almost nothing about inference uptime.

Keep:

```text
source_reliability
```

and:

```text
endpoint_reliability
```

separate.

---

# 40. Proof kernel 12/14 means do not say “all high priority complete”

The recent commit itself says:

```text
PK-01 Every claim links to a valid offer — FAIL
PK-07 Evidence links to valid observations — FAIL
```

while its commit message says:

> All high priority items complete.

Those are central Oracle invariants.

They are not low-priority cosmetic failures.

I'd make:

```text
proof kernel < 100%
```

automatically forbid:

```text
production certificate
verified oracle language
release tag
```

No override.

---

# 41. Organizational cleanup is now an actual priority

The architecture has stabilized enough that the repo should become boring.

Target root:

```text
README.md
AGENTS.md
MANIFEST.json
pyproject.toml
app/
mcp/
skills/
tests/
docs/
data/
```

Move exploratory historical documents into:

```text
docs/archive/
```

Have only:

```text
README
AGENTS
API
DATA-MODEL
TRUST
SCORING
OPERATIONS
TESTING
```

as active docs.

And replace hard-coded counts in Markdown with generated sections.

---

# My proposed final taxonomy

I think this is the clean consumer product:

```text
FACTUAL TAGS
Free
Promo
Tool Capable
Vision Capable
JSON Capable
Long Context
OpenAI Compatible

MEASURED TAGS
Low Latency
High Throughput
Reliable Endpoint
Tool Proven
Long-Context Proven

QUALITY TAGS
Coding Strong
Reasoning Strong
Agent Strong
Frontier Coding
Frontier Reasoning

DECISION LABELS
Workhorse
High Value
Cheapest Sufficient
Best Free Capacity
```

And the first three layers can exist independently.

The last layer **must always be workload/context dependent**.

---

# What I'd tell the Dell agent now

Dell does **not need another feature phase**.

It needs a semantic-hardening phase:

```text
P0
REST and MCP one canonical service

P0
remove accepted-but-ignored filters

P0
unknown can never satisfy hard requirements

P0
fix FreeCompute quota/context math

P0
proof kernel back to 14/14

P1
one scoring implementation only

P1
replace raw benchmark median with normalized task profiles

P1
separate capability/support from measured quality

P1
redesign Workhorse as route-level, evidence-penalized composite

P1
rename/remove misleading badges

P1
field-specific freshness for /live

P1
canonical /resolve endpoint

P2
generate REST/MCP docs from schemas

P2
formal Hermes skills + permission boundaries

P2
category/badge semantic mutation suite

P2
consumer response envelope + explanation/exclusion reasons

P2
archive all stale duplicate docs/servers
```

After **that** I would call Dell's consumer/API design essentially finished.

The central design principle should be:

> **Dell never tells an agent that something is “best,” “fast,” “agentic,” “free,” “live,” or even “usable” unless it can define precisely what that word means, show the fields used to derive it, distinguish measured from inferred values, and explain which alternatives were excluded and why.**

That would make Dell unusually good infrastructure rather than another model-ranking site with nicer provenance.

[1]: https://github.com/OpenRouterTeam/skills/blob/main/skills/openrouter-benchmarks/SKILL.md?utm_source=chatgpt.com "skills/skills/openrouter-benchmarks/SKILL.md at main · OpenRouterTeam/skills · GitHub"
[2]: https://aclanthology.org/2026.findings-acl.1881/?utm_source=chatgpt.com "LLMRouterBench: A Massive Benchmark and Unified Framework for LLM Routing - ACL Anthology"
[3]: https://openrouter.ai/docs/guides/routing/provider-selection?utm_source=chatgpt.com "Provider Routing | Intelligent Multi-Provider Request Routing | OpenRouter | Documentation"
[4]: https://arxiv.org/abs/2410.02694?utm_source=chatgpt.com "HELMET: How to Evaluate Long-Context Language Models Effectively and Thoroughly"
