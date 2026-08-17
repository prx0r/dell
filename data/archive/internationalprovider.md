# International Providers — Regional Radar

**Regional-language crawling is a competitive advantage. Some of the best offers are barely visible in English.**

## Live Deals (August 2026)

| Region | Provider | Opportunity | Radar |
|--------|----------|-------------|-------|
| 🇨🇳/Global | **SenseNova** | 1,500 calls/model/5h, $0 public beta | 🔥🔥🔥🔥🔥 |
| 🇯🇵 Japan | **Sakura AI Engine** | 3,000 chat req/month free, monthly reset | 🔥🔥🔥🔥🔥 |
| 🇹🇭 Thailand | **Typhoon** | Rate-limited free hosted API for Thai models | 🔥🔥🔥🔥 |
| 🇰🇷 Korea | **Upstage** | $10 signup credit + temporary free APIs | 🔥🔥🔥🔥 |
| 🇫🇷 France | **Scaleway** | 1M serverless inference tokens free | 🔥🔥🔥🔥 |
| 🇫🇷 France | **OVHcloud** | $200 signup credits on AI Endpoints | 🔥🔥🔥🔥 |
| 🇮🇱 Israel | **Aion Labs** | Daily free API credits, no card | 🔥🔥🔥🔥 |
| 🇧🇷 Brazil | **Maritaca** | Up to 50% off overnight/batch inference | 🔥🔥🔥🔥 |
| 🇮🇳 India | **Sarvam** | Free dev credits + 6-12mo startup credits | 🔥🔥🔥 |
| 🇨🇳 China | **Alibaba Bailian** | Per-model newcomer quotas | 🔥🔥🔥 |
| 🇨🇳 China | **Infini-AI** | Embeddings + reranker API free | 🔥🔥🔥 |
| 🇨🇳 China | **SiliconFlow** | Experience credits + partner free-model quotas | 🔥🔥🔥 |

## Source URLs to Crawl

### Tier-0 (monitor daily)
- SenseNova: https://www.sensenova.ai/token-plan
- Sakura AI: https://cloud.sakura.ad.jp/
- Upstage: https://www.upstage.ai/pricing/api
- Scaleway: https://www.scaleway.com/en/generative-apis/
- OVHcloud: https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-capabilities
- Aion Labs: https://www.aionlabs.ai/pricing/
- Maritaca: https://www.maritaca.ai/planos/

### Tier-1 (monitor weekly)
- Typhoon: https://opentyphoon.ai/
- Sarvam: https://www.sarvam.ai/
- SiliconFlow: https://docs.siliconflow.cn/cn/release-notes/overview
- Infini-AI: https://docs.infini-ai.com/
- MiniMax Token Plan: https://platform.minimax.io/subscribe/token-plan
- Tencent Token Plan: https://intl.cloud.tencent.com/document/product/1300/81315

## Native Language Search Vocabulary

### Chinese
免费额度, 免费调用, 免费试用, 限时免费, 公测, 优惠, 特惠, 福利, 代金券, 赠送额度, 新人, 首购优惠, 充值返, 套餐, Token 福利包, Coding Plan, Token Plan, 降价, 调价, 限时放量

### Japanese
無料, 無料枠, 無償, キャンペーン, 期間限定, お試し, 新規登録, クレジット, 割引, API 無料, 生成AI 無料枠

### Korean
무료, 무료 크레딧, 무료 사용, 체험, 프로모션, 할인, 가입 크레딧, API 무료

### Portuguese
gratuito, créditos grátis, teste grátis, promoção, desconto, novos usuários, API gratuita, créditos API

### Thai
ฟรี, ทดลองฟรี, เครดิตฟรี, API ฟรี, โปรโมชั่น, ส่วนลด

## Regional Eligibility Schema

```json
{
  "global_access": "yes|likely|no|unknown",
  "local_phone_required": false,
  "local_card_required": false,
  "local_id_required": false,
  "business_only": false,
  "kyc_required": false,
  "automation_allowed": true,
  "backend_allowed": true,
  "openai_compat": true,
  "anthropic_compat": false,
  "source_language": "en|zh|ja|ko|th|pt|hi|ar|id|vi|es|fr"
}
```

## Time-Window Deals

Maritaca has 50% off overnight/batch. Alibaba has off-peak 0.2× multiplier (5× effective usage). These need:
```json
{
  "deal_type": "off_peak",
  "discount_max": 0.50,
  "conditions": ["night", "batch"],
  "timezone": "America/Sao_Paulo"
}
```

## Dead Deals to Track
- Infini-AI LLM API: STOPPED 2026-03-30 (embeddings/reranker remain free)
- GitHub Models: STOPPED 2026-07-30
