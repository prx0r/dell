# Peer Review V2 — Architecture Overhaul

## Core Insight

**Dell must catalog actual executable inference routes, not models with price annotations.**

## The 27 Issues

### 1. Delete author→provider inference
Model author ≠ serving provider. `deepseek/deepseek-*` through OpenRouter is served by OpenRouter, not DeepSeek.

### 2. Unknown quantization ≠ Full precision
NULL quantization = UNKNOWN. Never infer.

### 3. Add serving_endpoints table
Model → Route → Serving Endpoint. Each endpoint has its own quantization, context, pricing, performance.

### 4. OpenRouter has /endpoints API
`GET /api/v1/models/{author}/{slug}/endpoints` gives provider_name, tag, quantization, latency, throughput, uptime.

### 5. Free needs THREE concepts
- price = 0
- quota = conditional (50 RPD baseline, 1000 RPD if $10+ credits)
- availability = variable

### 6. Separate public entitlement from user entitlement
- GLOBAL POLICY: "What does this service advertise?"
- ACCOUNT STATE: "What does THIS USER currently have?"

### 7. Cloudflare is excellent second provider
10,000 Neurons/day free, model-specific limits, changelog.

### 8. Hugging Face = recurring credits
$0.10/month free credits, not "free models."

### 9. Gemini = account-dependent quota
RPM/TPM/RPD, resets at midnight Pacific, preview models more restrictive.

### 10. Groq = ideal for Dell
Documents per-model limits (RPM/RPD/TPM/TPD), exposes rate-limit headers.

### 11. Provider-capability pipeline
```python
class ProviderIntelligenceAdapter:
    def discover_models() -> list[ModelObservation]: ...
    def discover_endpoints() -> list[EndpointObservation]: ...
    def discover_pricing() -> list[PriceObservation]: ...
    def discover_quotas() -> list[QuotaPolicy]: ...
    def probe_account() -> AccountState | None: ...
```

### 12. Source hierarchy
- TIER A: official machine API
- TIER B: official structured docs
- TIER C: authenticated account observation
- TIER D: Dell synthetic probe
- TIER E: browser inspection
- TIER F: blogs/Reddit (discovery only)

### 13. Hermes finds unknowns, not replaces APIs
Build completeness record per endpoint. Only investigate UNKNOWN or STALE fields.

### 14. context_advertised ≠ context_effective
Have: advertised, endpoint_max, probe_passed, probe_failed, effective_estimate.

### 15. Measure ugly stuff yourself
Probes: health, structured output, tool calling, context ladder, concurrency.

### 16. Performance needs history
Store: endpoint, timestamp, ttft, throughput, status, 429. Derive p50/p90 over windows.

### 17. Free Utility calculation
```python
utility = quality * capacity_fit * reliability * speed
```
Don't divide by zero for free routes.

### 18. effective_free_capacity
Per task: "Can this free route actually complete my job?"

### 19. Canonical states
- quantization: KNOWN | UNKNOWN | VARIABLE
- availability: AVAILABLE | DEGRADED | UNAVAILABLE | UNKNOWN
- free: ZERO_PRICE | CREDIT_BACKED | ALLOWANCE_BACKED | PROMOTIONAL | UNKNOWN
- quota: KNOWN_STATIC | KNOWN_CONDITIONAL | ACCOUNT_DEPENDENT | MEASURED | UNKNOWN

### 20. Remove "Full precision" output
NULL = UNKNOWN. Never infer.

### 21. Don't invent "slowdown = yes/no"
Store throughput_p50/p90, TTFT_p50/p90, availability, 429_rate. Derive performance_class.

### 22. OpenRouter implementation order
OR-1 through OR-10: poll models, extract free variants, poll endpoints, persist, derive capacity.

### 23. Cron schedule
- OpenRouter models: 30 min
- OpenRouter free endpoints: 10 min
- Cloudflare limits: 6 h
- Groq limits: 6 h
- Dell canaries: 15 min

### 24. Nightly FREE INTELLIGENCE GAP REPORT
Output: fully characterized, missing quota, missing quantization, missing performance.

### 25. Provenance class
Every fact has: value, unit, source, authority, observed_at, confidence.

### 26. Real route object for recommender
Not "model = DeepSeek, price = 0" but full route with performance, capabilities, quantization.

### 27. /v1/free/plan endpoint
Input: task, requests, token volumes, requirements. Output: recommended routes that can actually complete the job.

## Immediate Tasks (1-10)
1. Delete author→provider inference
2. Unknown quantization = UNKNOWN
3. Add serving_endpoints table
4. Implement OpenRouter /endpoints API
5. Add quota_policies table
6. Model free as 3 concepts
7. Add effective_free_capacity
8. Add provenance class
9. Implement /v1/free/plan endpoint
10. Nightly gap report
