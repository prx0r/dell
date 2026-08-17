# Deal Investigation Protocol

When Hermes finds a new deal, it doesn't just record it — it investigates.

## The Investigation Pipeline

```
NEW DEAL DETECTED
    ↓
ROUND 1: Identify the deal
  - What model? What provider? What's the offer?
  - Extract: price, quota, multiplier, context
    ↓
ROUND 2: Find ALL sources
  - Search web for "[provider] [model] pricing"
  - Check provider's official pricing page
  - Check provider's blog/changelog
  - Check OpenRouter for cross-provider data
  - Check models.dev for benchmarks
  - Check HN/Reddit for community reports
    ↓
ROUND 3: Extract exact details
  - Start date: when was this deal first seen?
  - End date: when does it expire? (if known)
  - Terms: what are the restrictions?
  - Eligibility: who can use it? (region, card, KYC)
  - Quota: exact rate limits
    ↓
ROUND 4: Verify against official source
  - Does the official page confirm this deal?
  - Is the deal still active?
  - Are the terms accurate?
  - What's the verification confidence?
    ↓
ROUND 5: Record with full evidence
  - Store: all sources, all timestamps, all terms
  - Create: CandidateVerificationBundle
  - Link: every claim to its evidence
```

## What Each Round Produces

### Round 1: Identification
```json
{
  "deal_id": "opencode-go:gpt-5.6-luna:2x-usage",
  "model": "gpt-5.6-luna",
  "provider": "opencode-go",
  "deal_type": "usage_multiplier",
  "multiplier": 2.0
}
```

### Round 2: Source Discovery
```json
{
  "sources": [
    {"url": "https://dev.opencode.ai/go", "type": "official", "language": "en"},
    {"url": "https://openrouter.ai/models", "type": "structured_api"},
    {"url": "https://models.dev/openai/gpt-5.6-luna", "type": "metadata"},
    {"url": "https://news.ycombinator.com/item?id=...", "type": "community"}
  ]
}
```

### Round 3: Details Extraction
```json
{
  "start_date": null,
  "end_date": null,
  "terms": "Limited time promotion",
  "eligibility": {"global": true, "card_required": false},
  "quota": {"requests_per_5h": 4100},
  "context": 1050000
}
```

### Round 4: Verification
```json
{
  "official_source": "https://dev.opencode.ai/go",
  "status": "LIVE_AS_OF_CHECK",
  "confidence": 0.95,
  "checked_at": "2026-08-17T16:00:00Z"
}
```

### Round 5: Full Record
```json
{
  "deal_id": "opencode-go:gpt-5.6-luna:2x-usage",
  "identification": {...},
  "sources": [...],
  "details": {...},
  "verification": {...},
  "first_seen": "2026-08-17T14:37:00Z",
  "last_verified": "2026-08-17T16:00:00Z"
}
```

## How Twitter Fits In

Once hooked up:
1. Monitor provider Twitter accounts for deal announcements
2. Search Twitter for "LLM API free" / "2x usage" etc.
3. Extract: deal type, model, provider, link
4. Feed into investigation pipeline
5. Verify against official sources
6. Store with full evidence trail

## The Key Insight

Don't just record "Luna has 2x usage."
Record:
- WHEN was it first seen?
- WHERE was it confirmed?
- What are the exact terms?
- When does it end?
- How confident are we?
- What evidence supports this?
- What's the alternative if this deal ends?

That's what makes it infrastructure, not a scraper.
