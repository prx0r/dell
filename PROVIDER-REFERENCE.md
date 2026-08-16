# LLM PROVIDER REFERENCE — the complete source registry (verified 2026-08-15)

*The canonical guide to every LLM-inference source worth tracking in the deal-radar. Verified (real
endpoints, keys, pricing) vs marketing. Tiers: what to ADD, what to track with caution, what to EXCLUDE.
This is the reference the deal-radar ingests + the model router routes over.*

---

## TIER 1 — GENUINELY USABLE OpenAI-compatible APIs (add to the registry)

| Provider | Base URL | Free tier | Key | Notes |
|---|---|---|---|---|
| **Hugging Face Inference** | `router.huggingface.co/v1` | **$0.10/mo free, $2 PRO** | HF token (`inference.serverless.write`) | ⭐ **BEST single add**: one key, hundreds of models, per-provider pricing via `GET /v1/models`, auto-failover. Effectively a free OpenRouter. |
| **AkashML** | `api.akashml.com/v1` | trial credits | Bearer key | ⭐ **Cheapest open models** (DeepSeek V4 Flash $0.14/$0.28, GLM-5.2 $0.77/$2.42 promo). Drop-in OpenAI/Anthropic. |
| **Together AI** | `api.together.xyz/v1` | free + credits | key | Hosts most frontier open models (DeepSeek, GLM-5.2 $1.40/$4.40, MiniMax M3). |
| **Mistral La Plateforme** | `api.mistral.ai/v1` | free tier (Studio) | key | Small models (mistral-small/ministral) + 3rd-party open models. |
| **DeepInfra** | `api.deepinfra.com/v1` | no free, cheap | key | Serves most open models. |
| **Fireworks** | `api.fireworks.ai/v1` | cheap open | key | Fast open-model hosting. |
| **Google Gemini (AI Studio)** | `generativelanguage.googleapis.com/v1beta` + `/openai/` compat | **free tier** (shrinking) | aistudio key | Gemini 3.x/2.5, Flash-Lite. Free tier cut 250→~20 RPD; NOT reliable for batch. |
| **Perplexity Router** | `api.perplexity.ai` | no free (card) | key | Multi-provider zero-markup (openai/anthropic/google/xai prefixed), Sonar models. |
| **Groq** | `api.groq.com/openai/v1` | **free token allowances** | key | Ultra-fast, Llama 3.3 70B on free tier. |
| **Cerebras** | `api.cerebras.ai/v1` | free tier | key | Ultra-fast open models. |
| **Z.ai** | `api.z.ai/...` | GLM-5.2 free tier | key | GLM models, OpenAI-compatible. |

---

## TIER 2 — REAL INFRASTRUCTURE BUT NOT HOSTED LLM APIs (exclude from a model router)

| Provider | What it is | Why exclude |
|---|---|---|
| **io.net** | RAW GPU marketplace (Solana) | Rent GPUs + self-host vLLM. No hosted API. |
| **Salad Cloud** | Container platform on consumer GPUs | No hosted LLM chat API (only a Whisper transcription API). |
| **Vast.ai** | RAW GPU marketplace | Rent by hour, self-host. Not an API. |
| **Petals** | distributed, slow, free | Research-grade, keep as free fallback only. |

---

## TIER 3 — DECENTRALIZED / WEB3 (real but awkward — edge cases)

| Provider | Reality | For a router? |
|---|---|---|
| **GaiaNet** | P2P nodes, each an OpenAI-compat endpoint (`<nodeid>.us.gaianet.network/v1`) | ❌ no unified billing/models/uptime — tracking hundreds of volatile node URLs |
| **Bittensor (TAO)** | Functional blockchain, **NOT an LLM API** — no OpenAI endpoint, no keys/REST/pricing | ❌ exclude (vaporware as an API product) |
| **Corcel** | Real API (`api.corcel.io`, OpenAI-compat), docs JS-gated | ⚠️ verify live before adding |

---

## TIER 4 — AI-SEARCH / CRYPTO-AI (mostly NOT inference APIs)

| Provider | Reality |
|---|---|
| **Kaito.ai** | ❌ NOT an LLM API — attention-economy/social-mindshare analytics (Yapper, airdrops) |
| **Perplexity** | ✅ real API (see Tier 1) — not just search |

---

## THE SHORTLIST (what the deal-radar should track)

**Add now (real OpenAI-compatible):**
- `router.huggingface.co/v1` (best free tier + pricing metadata)
- `api.akashml.com/v1` (cheapest open models)
- `api.together.xyz/v1`, `api.mistral.ai/v1`, `api.deepinfra.com/v1`, `api.fireworks.ai/v1`
- `generativelanguage.googleapis.com` (Gemini — free-tier caveat)
- `api.perplexity.ai` (Router)

**Exclude:** Bittensor, Kaito, io.net, Vast, Salad (raw compute / not inference), GaiaNet (P2P chaos).

---

## THE INGESTION PATTERN (how to add a provider to the deal-radar)

```python
# 1. add to rate_limits.FREE_QUOTAS (if it has a free tier)
FREE_QUOTAS["huggingface"] = {"rpm": None, "rpd": None, "tokens_per_day": None,
                              "note": "$0.10/mo free credits, $2 PRO"}
# 2. add an OpenRouter/models.dev listing (auto-ingested) OR a dedicated probe
# 3. add a canary probe (app/canary.py) to verify it's live
# 4. the model router picks it up automatically (tensions + utility engine)
```

*This is the provider source registry. The deal-radar ingests Tier-1 providers, tracks Tier-3 with
caution, and excludes the non-API Tier-2/4. The HF router is the single best addition — one key,
hundreds of models, per-provider pricing.*
