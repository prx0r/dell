# Integration Spec: Alternatives → LLM Deals

## How We Integrate With Each Alternative

### models.dev (Static catalog → Temporal layer)
**What we add:**
- Live polling (vs static)
- Deal detection (vs catalog only)
- Quota tracking (vs none)
- Regional data (vs none)
- Change detection (vs snapshot)

**Integration:** models.dev provides benchmarks + capabilities. We enrich with pricing, quotas, deals, temporal tracking.

### OpenRouter (Single-provider → Cross-provider)
**What we add:**
- Cross-provider aggregation (vs their single catalog)
- Deal detection across all providers
- Free tier qualification
- Regional eligibility
- Activation recipes

**Integration:** OpenRouter provides real-time pricing + free model list. We add temporal layer + multi-provider view.

### awesome-free-llm-apis (Static list → Live polling)
**What we add:**
- Live verification (vs static list)
- Change detection (vs snapshot)
- Rate limit tracking (vs none)
- Provider health monitoring

**Integration:** Their list is a seed. We poll live, verify, and track changes.

### PricePerToken (Price comparison → Full deal tracking)
**What we add:**
- Deal types (not just prices)
- Quota/credit tracking
- Regional eligibility
- Temporal history
- Activation recipes

**Integration:** They compare prices. We track everything else.

### LLM Router (Routing algorithms → Data layer)
**What we add:**
- The data layer they route over
- Live pricing + quotas
- Deal detection
- Provider health

**Integration:** They consume our data. We don't compete.

### LiteLLM (Infrastructure → Data)
**What we add:**
- The data LiteLLM consumes
- Deal detection
- Quota tracking
- Regional eligibility

**Integration:** We provide the data layer. They provide the proxy.

## Auto-Router Architecture (Future)

```
LLM Deals Data Layer
        ↓
   Auto-Router
   ├── Task classification
   ├── Model selection
   ├── Provider routing
   ├── Quota management
   ├── Fallback chains
   └── Cost optimization
        ↓
   LiteLLM/Bifrost (execution)
```

The Auto-Router uses our data to make routing decisions. We don't execute inference — we provide the intelligence.
