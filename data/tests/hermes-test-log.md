# Hermes Test Log
**Date:** $(date)
**Test:** End-to-end skill + kanban + MCP integration

---

## Test 1: Discovery Skill
## Test 1: Discovery

## Test 2: Investigation

## Test 3: Validation
Validation complete. Here's the report:

```json
{
  "deal_id": "deepseek-v4-flash",
  "source_url": "https://openrouter.ai/models?q=deepseek-v4-flash",
  "status": "NOT FREE",
  "confidence": 0.99,
  "checked_at": "2026-08-17",
  "evidence": "All 3 DeepSeek V4 Flash variants on OpenRouter have non-zero pricing. None are free."
}
```

FINDINGS:

DeepSeek V4 Flash is NOT free on OpenRouter. Three variants are listed:

  Variant                          | Input/M   | Output/M  | Free?
  ---------------------------------|-----------|-----------|------
  deepseek/deepseek-v4-flash       | $0.0798   | $0.1596   | NO
  deepseek/deepseek-v4-flash-0731  | $0.1400   | $0.2800   | NO
  ~deepseek/deepseek-v4-flash-latest | $0.0786 | $0.1572   | NO

The cheapest variant (~deepseek-v4-flash-latest) costs $0.0786/M input
and $0.1572/M output — significantly cheap, but definitely not free.

The page showed "44% off" on the 0731 variant, indicating a discount
from its normal price, not a free tier.

VERDICT: If this deal was previously tracked as "free" on OpenRouter,
it should be marked as EXPIRED or CHANGED. DeepSeek V4 Flash is
currently a paid (discounted) model, not free.

## Test 4: MCP Tools
Here are the results:

=== 1. get_dataset_stats ===
Total offers: 1853
Free offers: 632
Providers: 65

=== 2. get_free_models (limit=3) ===

1. openai/gpt-4o
   Provider: openai
   Offer: metered_api
   Context: 128K tokens
   Features: tool_call=true, structured_output=true
   Modalities: text, image, pdf

2. openai/gpt-image-1.5
   Provider: openai
   Offer: metered_api
   Context: 0 tokens (image model)
   Modalities: image, text

3. openai/gpt-5.3-chat-latest
   Provider: openai
   Offer: metered_api
   Context: 128K tokens
   Features: tool_call=true, structured_output=true
   Released: 2026-03-03

=== 3. explain_deal: opencode-go/gpt-5.6-luna ===

Provider: opencode-go
Model: opencode-go/gpt-5.6-luna
Offer type: usage_multiplier
Deal status: active
Requests per 5h: 4100
Usage multiplier: 2.0x
Capacity vs median: 1.3x
Source: https://dev.opencode-go.ai/go
Not free — but offers 2x usage multiplier and higher capacity.

## Test 5: Kanban
By status:
  triage    0
  todo      0
  scheduled  0
  ready     0
  running   0
  blocked   1
  done      0

By assignee:
  patala                blocked=1
By status:
  triage    0
  todo      0
  scheduled  0
  ready     0
  running   0
  blocked   1
  done      0

By assignee:
  patala                blocked=1
By status:
  triage    0
  todo      0
  scheduled  0
  ready     0
  running   0
  blocked   1
  done      0

By assignee:
  patala                blocked=1

## Test Complete
