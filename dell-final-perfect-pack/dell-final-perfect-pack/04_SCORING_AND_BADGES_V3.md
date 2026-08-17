# Scoring and Badge Semantics V3

## Rule 1: rankings are task/workload dependent

Do not expose one universal intelligence score as truth.

Maintain domain profiles:

- coding
- reasoning
- research
- agentic/tool-use
- long-context
- multimodal
- instruction following

Raw benchmark scores should be stored as facts.

If combining benchmarks, normalize within benchmark/version before aggregation.

## Rule 2: Workhorse is a route-level decision label

Definition:

> An economical, dependable route capable of sustaining broad repetitive workloads without a major quality, capability, context, reliability, throughput or quota bottleneck.

Eligibility before score:

- route active enough for chosen evidence policy
- price/economic mechanism known enough
- minimum quality evidence threshold
- requested capabilities satisfied
- quota/capacity state usable or explicitly unknown-policy allowed
- no hard endpoint failure

Candidate dimensions:

- task/breadth quality
- workload economics
- endpoint reliability
- sustained throughput
- capacity/quota adequacy
- capability adequacy

Use geometric/bottleneck-aware aggregation only on normalized dimensions.

Missing dimensions:
- mandatory missing => ineligible
- optional missing => confidence penalty
- never disappear from denominator and improve a score

## Rule 3: confidence is not coverage

Coverage:
fraction of required fields/dimensions having qualifying evidence.

Confidence:
strength/quality of the evidence supporting those fields, e.g. source authority, measurement sample size, recency, variance, corroboration.

Do not set both to `number_of_dimensions_present / total`.

## Rule 4: capability is factual

Capability should not contain:
- free status
- price
- context as a quality bonus
- arbitrary baseline 50

Represent:

```json
{
  "tools": "TRUE|FALSE|UNKNOWN",
  "json_schema": "TRUE|FALSE|UNKNOWN",
  "vision": "TRUE|FALSE|UNKNOWN",
  "streaming": "TRUE|FALSE|UNKNOWN"
}
```

Measured quality is separate:

```json
{
  "tool_success_rate": 0.94,
  "json_schema_success_rate": 0.98
}
```

## Rule 5: source health != endpoint reliability

Keep:
- collector/source availability
- provider control-plane health
- inference endpoint success rate

as distinct predicates.

A source URL containing a trusted brand must never produce a numeric reliability score.

## Recommended public badges

### Factual
- Free
- Promo
- Tool Capable
- Vision Capable
- JSON Capable
- Long Context
- OpenAI Compatible

### Measured
- Low Latency
- High Throughput
- Reliable Endpoint
- Tool Proven
- JSON Proven
- Long-Context Proven

### Quality
- Coding Strong
- Reasoning Strong
- Agent Strong
- Frontier Coding
- Frontier Reasoning

### Decision labels
- Workhorse
- High Value
- Cheapest Sufficient
- Best Free Capacity

## Badge engine contract

Badge predicates receive a typed `RouteAssessment`, not an arbitrary dimensions dict.

Example:

```json
{
  "facts": {...},
  "measurements": {...},
  "quality": {...},
  "economics": {...},
  "decision_metrics": {...},
  "evidence": {...}
}
```

Every badge response includes:

```json
{
  "id": "reliable_endpoint",
  "basis": [
    {"field": "endpoint_success_rate", "value": 0.992}
  ],
  "evidence_ids": ["..."],
  "as_of": "..."
}
```

## Semantic mutation tests

- Unknown tool capability must never satisfy `tools=required`.
- Missing price must never become free.
- RPD must never affect TPS badge.
- Source fetch success must never create Reliable Endpoint.
- Advertised context must never create Long-Context Proven.
- Popularity must never create quality.
- Free status must never increase capability score.
- Expired promo must immediately lose Promo/Deal labels.
- A route missing reliability cannot outrank an otherwise equivalent measured reliable route because of missing-data arithmetic.
