# fx: Frontier Model Deal Intelligence

**Prefix:** `fx`
**Version:** 1.0.0
**Status:** Production-ready

---

## Mission

When a provider changes a model, multiplier, quota, price, context window, routing policy,
or access tier, determine where the new value actually is.

Do not merely report that a deal exists. Answer:

- What exactly changed?
- What does the user really receive per dollar / per quota period?
- Is the headline multiplier actually correct?
- How capable is the model on the workloads that matter?
- What are its failure modes and operational quirks?
- Does it replace the previous best-value model, or only become best for one role?
- What should an agent/router do differently because of the change?
- What evidence would falsify the recommendation?

**The central principle:**

> The best model is usually a routing decision, not a leaderboard position.

A model can be the best orchestrator while being terrible value as a bulk executor. A
cheaper model can be inferior at open-ended reasoning but overwhelmingly superior for
repo-wide mechanical work. The job is to discover these role boundaries.

---

## Trigger Conditions

Use this skill when you encounter any of the following:

- provider adds a new model;
- usage multiplier changes (2x, 6x, 8x, etc.);
- subscription quota changes;
- model price changes;
- a new free / promotional endpoint appears;
- context window changes;
- rate limit changes;
- provider switches inference backend;
- model gains tool use / vision / caching / structured output;
- a model has a new release or checkpoint;
- community claims a model has suddenly become the best deal;
- user asks "X vs Y—which should I use?";
- user asks whether a change alters the overall cheapest or highest-value stack.

---

## Evidence Hierarchy

Never flatten all sources into the same confidence level.

### Tier A — Authoritative Product Facts

Prefer:
- provider pricing/quota documentation;
- official model card;
- official release announcement;
- official API/model catalog;
- official GitHub repository;
- provider status/changelog.

Use these for:
- price;
- context size;
- quota;
- supported modalities;
- advertised benchmark numbers;
- model architecture;
- launch date;
- explicit product limitations.

**Official claims are facts about what the vendor claims, not proof of real-world quality.**

### Tier B — Reproducible Independent Evidence

Prefer:
- public GitHub evaluation repositories;
- exact prompts and outputs;
- benchmark harnesses;
- issue threads with reproducible bugs;
- independent tests that expose methodology;
- public traces / logs / artifacts.

This evidence is especially valuable for:
- tool-call behavior;
- actual OpenCode/Cline/Claude Code behavior;
- instruction following;
- coding-agent persistence;
- browsing/research accuracy;
- endpoint quirks;
- image support that differs from advertised capability;
- provider-specific model behavior.

**One carefully documented real agent task can be more informative than a synthetic score
for a specific workflow.**

### Tier C — Structured Benchmark Evidence

Use:
- SWE-Bench variants;
- Terminal-Bench;
- LiveCodeBench;
- BFCL/tool-use benchmarks;
- long-context evaluations;
- relevant domain-specific evaluations.

Always ask:
- which exact benchmark variant?
- model vs provider endpoint?
- thinking budget?
- agent scaffold?
- pass@1 or repeated attempts?
- contamination risk?
- vendor-reported or independently reproduced?

### Tier D — Community Reports

Reddit, X, Discord, forums and anecdotal developer comments are discovery sources.

Use them to identify hypotheses such as:
- "model loops on edits";
- "tool calls fail after 100k tokens";
- "endpoint is throttled at night";
- "vision unexpectedly works."

**Do not promote the claim to a fact without corroboration where possible.**

---

## Research Passes

Run research in distinct passes. Do not start by trying to write the conclusion.

### Pass 1 — Establish the Deal Mechanically

Retrieve:
- subscription price;
- dollar-equivalent usage pool if applicable;
- token prices;
- request-equivalent estimates;
- multiplier;
- context window;
- max output;
- modalities;
- caching behavior;
- rate limits;
- reset period;
- regional restrictions;
- whether requests are routed to a different checkpoint/provider.

**Calculate normalized economics.**

Useful measures:
```
requests_per_dollar
output_tokens_per_dollar
input_tokens_per_dollar
estimated_typical_requests_per_month
estimated_agent_turns_per_5h_window
cost_of_100k_input_10k_output_task
cost_of_1m_context_repo_read
```

If provider publishes "typical request" estimates, preserve their assumptions rather than
pretending they are universal.

### Pass 2 — Resolve Headline Discrepancies

Search the exact contentious phrase.

Examples:
```
"8x" "OpenCode Go"
"6x" "OpenCode Go"
"Hy3" "OpenCode Go"
"MiMo-V2.5" usage multiplier
```

If marketing, provider docs and community posts disagree:
- identify the date of each statement;
- prioritize the latest official documentation for current product behavior;
- explain why an older number is still circulating;
- preserve uncertainty if the provider is dynamically changing limits.

**Never silently choose the number that makes the comparison more exciting.**

### Pass 3 — Establish Model Identity

Confirm:
- exact model name;
- checkpoint/version;
- release date;
- architecture;
- total vs active parameters for MoE;
- context;
- modalities;
- training/post-training focus;
- stated agent/tool optimizations.

**A provider label may map to a model that differs from the public checkpoint.**

### Pass 4 — Capability Evidence

Collect both:

**Broad benchmark evidence**
- Coding, tool use, reasoning, long context, multimodal, etc.

**Workflow-specific evidence**
Search for tests using the same host/framework as the user:
```
"Hy3" OpenCode benchmark
"MiMo-V2.5" OpenCode comparison
"Hy3" agent tool calls
"MiMo-V2.5" repo coding
```

**Framework-specific evidence matters** because an excellent base model can perform badly
through one provider's tool schema, truncation behavior or context implementation.

### Pass 5 — Inspect Actual Traces

If an evaluation repo exists, do not stop at its README conclusion.

Look for:
- prompts;
- model outputs;
- tool-call counts;
- retries;
- errors;
- tasks passed incorrectly;
- false confidence;
- constraint violations;
- overlong answers;
- whether the model cross-checked facts;
- whether it noticed contradictions;
- whether it changed strategy after failure.

**These details are often the source of the most useful recommendation.**

### Pass 6 — Identify Comparative Advantage

Do not ask only "which is smarter?"

Ask:
- Which is better at deciding what to do?
- Which is better at doing lots of predetermined work?
- Which is better at recovering from failed tools?
- Which is cheaper to let run autonomously?
- Which survives long repositories?
- Which handles images?
- Which is less likely to hallucinate a completed task?
- Which is faster?
- Which consumes quota aggressively?

**Turn model differences into roles.**

### Pass 7 — Test Whether the Global Routing Strategy Changes

Compare the newcomer against the current stack, not just one opponent.

Example roles:
```
ORCHESTRATOR
BULK_EXECUTOR
CODING_ESCALATION
RESEARCHER
VISION
LONG_CONTEXT
FAST_CLASSIFIER
REVIEWER
```

A newly added model only matters globally if it displaces a current role winner or creates
a useful new routing tier.

---

## Value Model

Never equate "more requests" with "better deal."

Model effective value as:

```
EFFECTIVE_VALUE(workload) =
    success_probability
  × useful_work_per_success
  × autonomy_reliability
  × throughput
  / expected_cost
```

A more practical scoring approximation:

```
VALUE_SCORE =
  0.25 task_success
+ 0.20 agent_reliability
+ 0.15 instruction_following
+ 0.10 tool_recovery
+ 0.10 context_fit
+ 0.10 speed
+ 0.10 economic_efficiency
```

**Weights must change by workload.**

### Orchestrator Weighting

| Factor | Weight |
|--------|--------|
| reasoning / planning | high |
| error detection | high |
| tool recovery | high |
| research skepticism | high |
| price efficiency | medium |
| raw request count | low |

### Bulk Executor Weighting

| Factor | Weight |
|--------|--------|
| price efficiency | very high |
| request allowance | very high |
| coding competence | high |
| long context | high |
| reasoning brilliance | medium |

The conclusion can therefore legitimately be:

> Model A is better, but Model B is 7× cheaper in the plan, so A should supervise B rather
> than replace it.

---

## Agent Behavior Signals

When reading traces, explicitly score behaviors that static benchmarks miss.

### Persistence

Did it continue investigating after the first plausible answer?

### Epistemic Caution

Did it distinguish verified facts from guesses?

### Contradiction Handling

When two APIs/sources disagreed, did it notice?

### Strategy Adaptation

When a build/tool failed, did it try a materially different route?

### Workspace Awareness

Did it discover relevant existing files, skills, scripts or project conventions?

### Completion Honesty

Did it claim success without validating output?

### Constraint Retention

Did it preserve requirements across a long multi-turn task?

### Tool-Call Economy

More tool calls are neither automatically good nor bad.

Ask whether additional calls increased confidence or merely burned quota.

Example:
- 16 calls + resolves contradictory GitHub facts = useful persistence
- 16 calls + repeatedly queries same failed endpoint = waste

---

## Required Output Structure

When publishing a result, use approximately this structure.

### Opening Verdict

Two or three sentences max.

State:
- whether the new deal matters;
- what role it wins;
- whether it replaces the previous recommendation.

**Example pattern:**

> Hy3 is the more interesting reasoning/orchestration model, but MiMo remains the much
> stronger volume deal. I would not replace MiMo with Hy3; I would put Hy3 above it as the
> director.

### Correct the Headline First

If the user's quoted multiplier/price is inaccurate or stale, correct it immediately.

### Compact Comparison Table

Include only decision-relevant dimensions:
- quota
- context
- input/output economics
- tool/vision capability
- agent reliability
- best role

### Explain the Surprising Part

Examples:
- why the expensive model is still worth using;
- why the cheaper model shouldn't be the orchestrator;
- why one independent trace mattered;
- why a benchmark does not map to the user's workflow.

### Give the Routing Recommendation

Prefer an architecture over "winner/loser."

```
             ORCHESTRATOR
                  │
             cheap workers
             /          \
      coding worker   research worker
                  │
               reviewer
```

### Give Escalation Rules

Example:
1. MiMo first for routine implementation.
2. Escalate to Hy3 when requirements are ambiguous or repeated execution fails.
3. Escalate to stronger premium model only after Hy3 cannot resolve the blocker.

### State Uncertainty

Explicitly note:
- dynamic quotas;
- small independent sample sizes;
- provider-specific endpoint behavior;
- missing benchmark reproduction;
- likely future repricing.

---

## Anti-Hype Rules

- Never declare a model best from vendor benchmarks alone.
- Never declare a deal best from token price alone.
- Never assume an advertised context window is equally usable for agent work.
- Never mix base-model capability with one provider's endpoint quality.
- Never treat a request multiplier as workload-independent value.
- Never count extra tool calls as intelligence without checking what they accomplished.
- Never replace a cheap workhorse simply because another model wins difficult tasks.
- Always investigate whether the models are complementary.
- Always date the recommendation. These markets change fast.
- Preserve previous recommendations so later changes can be audited.

---

## Fast Mode

When time is limited, perform only these six operations:

1. Open current official provider pricing/quota page.
2. Open official model cards for both models.
3. Search for one reproducible comparison in the user's actual coding/agent framework.
4. Normalize monthly/request economics.
5. Identify each model's comparative advantage.
6. Ask whether the optimal answer is routing rather than replacement.

**This usually captures most of the value.**

---

## Deep Mode

For a publishable report:

1. Archive all source pages with timestamps.
2. Re-run public benchmark harnesses where practical.
3. Design 5–20 representative agent tasks.
4. Run each model multiple times.
5. Preserve prompts, tool traces, outputs and final artifacts.
6. Blind-score task outcomes where possible.
7. Measure token/request consumption and wall-clock latency.
8. Classify failures.
9. Calculate role-specific value scores.
10. Publish raw evidence alongside the narrative conclusion.

**Useful task classes:**
- ambiguous architecture
- repo-wide implementation
- bug diagnosis
- live web research
- fact reconciliation
- long-context repo comprehension
- tool recovery
- vision + code
- constraint-heavy editing
- verification/review

---

## The Core Heuristic

Whenever a new model/deal appears, ask in this order:

```
WHAT CHANGED?
      ↓
IS THE HEADLINE TRUE?
      ↓
WHAT DOES IT COST IN REAL WORKLOADS?
      ↓
WHAT CAN IT DO BETTER?
      ↓
WHAT DOES IT DO WORSE?
      ↓
WHERE DOES THAT ADVANTAGE MATTER?
      ↓
DOES IT REPLACE A CURRENT ROLE WINNER?
      ↓
OR DOES IT CREATE A BETTER ROUTER?
      ↓
WHAT EVIDENCE WOULD CHANGE THIS VERDICT?
```

**The last two questions are usually where the valuable analysis appears.**

---

## Quality Standard

A successful run should leave the reader knowing something more actionable than:

> "Model A scored higher than Model B."

It should instead produce something like:

> "Model A is more reliable at ambiguous investigation and tool recovery, but Model B
> delivers approximately an order of magnitude more work under this subscription. Use A
> to plan and audit; use B for bulk execution; escalate only the hard failures. This changes
> the previous stack by inserting A as the supervisor rather than replacing B."

**That is the level of analysis this skill exists to produce.**

---

## Integration with Dell

This skill should be triggered:

1. When `app/sources/opencode.py` detects a new multiplier
2. When `app/sources/rss.py` detects a deal signal
3. When `app/sources/hackernews.py` detects a model launch
4. When user asks for a comparison via API
5. When blog post generation is triggered

**Output format:**
- Store `deal_event` in `deal_events` table
- Store `model_role_assessment` in `model_roles` table
- Store `routing_change` in `routing_changes` table
- Generate blog post content for `web/src/content/blog/`

---

## Example: Hy3 vs MiMo-V2.5

See `/mnt/HC_Volume_106427611/dell/perfectanalysis.md` for the gold standard analysis
produced by this skill.