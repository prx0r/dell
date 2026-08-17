# More Providers — The Full Deal Landscape

**8 deal primitives:** permanent-free, daily renewable quotas, per-model signup pools, temporary introductory pricing, subscription subsidies, batch discounts, startup/research credits, decentralized-compute subsidies.

## Live Deals (August 2026)

| Deal | Type | Value | Radar |
|------|------|-------|-------|
| OpenCode Go | $5 first month, $10/mo; Luna 2× usage | 🔥🔥🔥🔥🔥 |
| OpenCode Zen | Multiple $0 API models | 🔥🔥🔥🔥🔥 |
| Z.AI | GLM Flash free, Coding Plan $18/mo | 🔥🔥🔥🔥🔥 |
| Alibaba Bailian | 1M free tokens per model, independent quotas | 🔥🔥🔥🔥🔥 |
| AkashML | $100 inference credits for new accounts | 🔥🔥🔥🔥🔥 |
| OpenRouter | 25+ free models; $10 deposit → 1000 req/day free | 🔥🔥🔥🔥 |
| Google Gemini | Free tier + 50%-off Batch | 🔥🔥🔥🔥 |
| Mistral | Free mode API, no card | 🔥🔥🔥🔥 |
| NVIDIA NIM | Free dev/prototyping endpoints | 🔥🔥🔥🔥 |
| Groq | Free tier + 50%-off Batch | 🔥🔥🔥🔥 |
| Cloudflare | 10K neurons/day free | 🔥🔥🔥🔥 |
| Kilo | Auto Free routes across free models | 🔥🔥🔥🔥 |
| Nous Portal | Free catalog + subscription 10% bonus | 🔥🔥🔥 |
| Cerebras | $5 trial, 30-day expiry | 🔥🔥🔥 |
| io.net | $100 decentralized GPU trial | 🔥🔥🔥 |
| Chutes | Up to $10K startup credits | 🔥🔥🔥 |
| Aethir | Compute grants + 50% partner discounts | 🔥🔥🔥 |
| Nosana | Free GPU credits | 🔥🔥🔥 |
| Together | Research + startup up to $50K | 🔥🔥🔥 |
| Fireworks | $1 signup credit | 🔥🔥 |
| Nebius | Token Factory free credits + research grants | 🔥🔥 |
| Novita | $10/$10 referral + $100 sandbox promo | 🔥🔥 |

## Source URLs to Crawl

### Tier-0 (monitor daily)
- OpenCode Go: https://opencode.ai/go
- OpenCode Zen: https://opencode.ai/docs/zen/
- OpenCode Data: https://opencode.ai/data/
- Z.AI Pricing: https://docs.z.ai/guides/overview/pricing
- Z.AI Coding Plan: https://docs.z.ai/devpack/overview
- Alibaba Bailian: https://help.aliyun.com/zh/model-studio/new-free-quota
- AkashML: https://akash.network/blog/akashml-managed-ai-inference
- Kilo Free Models: https://kilo.ai/landing/free-models
- Nous Portal: https://portal.nousresearch.com
- OpenRouter Free: https://openrouter.ai/collections/free-models

### Tier-1 (monitor weekly)
- Volcengine: https://www.volcengine.com/docs/82379/1399514
- Tencent TokenHub: https://cloud.tencent.com/document/product/1823/130053
- Baidu Qianfan: https://cloud.baidu.com/doc/qianfan/s/Omh4su4s0
- Google Gemini: https://ai.google.dev/gemini-api/docs/pricing
- Groq: https://console.groq.com/docs/rate-limits
- Cerebras: https://inference-docs.cerebras.ai/support/change-log
- NVIDIA NIM: https://developer.nvidia.com/nim
- Mistral: https://docs.mistral.ai/admin/billing-usage/subscriptions
- Cloudflare: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Together: https://www.together.ai/research-credits-program-request
- Fireworks: https://fireworks.ai/pricing
- Novita: https://novita.ai/referral
- Chutes: https://chutes.ai/pricing
- io.net: https://io.net
- Nosana: https://nosana.com
- Aethir: https://aethir.com/blog-posts/aethir-the-developers-gpu-cloud

### Tier-2 (check monthly)
- Nebius: https://nebius.com/nebius-research-grants
- SiliconFlow: https://siliconflow.cn
- Moonshot: https://platform.moonshot.cn
- DeepSeek: https://platform.deepseek.com

## Dead Deals to Track
- GitHub Models: DEAD (retired 2026-07-30)

## Deal Schema

```json
{
  "deal_id": "opencode:gpt-5.6-luna:2x:2026-08",
  "provider": "opencode",
  "product": "go",
  "model": "gpt-5.6-luna",
  "type": "usage_multiplier",
  "multiplier": 2,
  "status": "LIVE",
  "started_at": null,
  "ends_at": null,
  "eligibility": {
    "new_user": false,
    "subscription_required": true,
    "region": "global"
  },
  "restrictions": {
    "automation": true,
    "production": null
  },
  "verification": {
    "official": true,
    "last_checked": "2026-08-17T..."
  }
}
```

### Deal Types
- `permanent_free` — always free
- `renewable_free_quota` — resets daily/weekly/monthly
- `per_model_free_quota` — independent per model (Alibaba pattern)
- `signup_credit` — one-time credit on signup
- `usage_multiplier` — 2x/3x bonus (OpenCode pattern)
- `subscription_subsidy` — credits bonus on subscription (Nous 10%)
- `batch_discount` — 50% off for async (Google, Groq)
- `introductory_pricing` — temporary low price
- `startup_research_credit` — conditional (Together $50K, Chutes $10K)
- `decentralized_subsidy` — GPU credits (io.net, Nosana, Aethir)
- `dead` — no longer available
