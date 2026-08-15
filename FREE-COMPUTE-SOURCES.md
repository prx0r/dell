# EFFECTIVELY-UNLIMITED FREE INFERENCE — the compute-source classes

*2026-08-15 · the map of non-API free-compute sources (beyond commercial API free tiers). The key
insight: "effectively unlimited" comes from **who supplies the compute** (users, volunteers, browsers,
always-free VMs, platforms), not from a company burning unlimited GPU for you.*

---

## THE CLASSES (each a distinct router tier)

| Class | Method | Marginal cost | Unlimited? | Intelligence | The catch |
|---|---|---|---|---|---|
| **User-pays** | Puter.js | **$0** for your app | Yes, for your app | GPT/Claude/etc | each user supplies their allowance |
| **User-hardware** | WebLLM (WebGPU) / Chrome Prompt API | **$0** | Yes | small-medium open / Gemini Nano | uses user's GPU/RAM/browser |
| **Volunteer swarm** | Petals | **$0** | Nearly | up to Llama 3.1 405B | slow, variable, non-private |
| **Always-free VM** | Oracle A1 ARM | **$0** | Yes, continuously | small local models | CPU inference |
| **Batch GPU** | Kaggle (30 GPU hr/wk + 20 TPU hr/wk) | **$0** | large batch | whatever fits | batch/not persistent |
| **Collective** | HF ZeroGPU | **$0** | No | huge range | daily quota/queues |
| **Opportunistic** | Google Colab | **$0** | variable | GPUs/TPUs | dynamic, unguaranteed |

---

## THE THREE "HIDDEN GOLD" ONES

### 1. Petals — BitTorrent for LLM inference
Volunteers host different transformer layers; your request flows through the swarm. Llama 3.1 up to 405B.
No `$/M tokens` — community capacity. **Catch:** swarm availability, 4-6 tok/s, not private.
→ Best for bulk experimental research where speed doesn't matter.

### 2. Puter.js — unlimited-API loophole for APPS
Your app's AI bill stays $0 whether you have 1 or a million users — each user's requests are metered
against their OWN Puter allowance. 400+ models. **Catch:** for building a product it's great; for your
own personal use you're still one user.

### 3. WebLLM / Chrome Prompt API — literally unlimited browser inference
Runs the LLM in-browser on WebGPU (WebLLM) or local Gemini Nano (Chrome). No server, no API key, no
token bill, **no quota to exhaust** — the limit is the user's hardware. Perfect for the boring 80%
(classify, extract, rerank, summarize, RAG, JSON check, embeddings).

---

## THE COMBINED ARCHITECTURE (the realistic goal)

```
                    ┌── WebLLM ───────── unlimited $0 (user GPU)
                    ├── Chrome Nano ───── unlimited $0 (local)
                    ├── Oracle model ──── 24/7 $0 (ARM VM)
                    ├── Petals ────────── community $0
       FREE POOL ───┼── Groq ─────────── daily $0
                    ├── Z.AI ─────────── daily $0
                    ├── Kilo ──────────── hourly $0
                    ├── NVIDIA ───────── prototyping $0
                    └── Kaggle ───────── batch GPU $0
                          ↓ all unsuitable/exhausted
                    OpenCode Go / MiMo / Flash
                          ↓
                       Luna
                          ↓
                    expensive frontier
```

**The realization:** only a small fraction of tokens ever reach a paid endpoint — for a personal
research/coding system this becomes effectively unlimited cheap inference.

---

## WHAT'S INTEGRABLE INTO THE DEAL-RADAR NOW (honest)

| Source | Integrable from this box? | How |
|---|---|---|
| **Petals** | ⚠️ yes (pip + swarm network) | a `petals` compute-source tier (batch/research) |
| **WebLLM/Chrome** | ❌ no (browser-side) | documented tier; the API/site serves the client, inference is client-side |
| **Oracle A1** | ❌ no (needs account/VM) | documented tier: a self-hosted llama.cpp OpenAI-compatible endpoint |
| **Kaggle/Colab** | ❌ no (external platform) | documented batch tier |
| **Puter** | ⚠️ needs an app + Puter key | documented; model available via Puter's 400-model API |

The deal-radar should model these as **compute-source tiers** (distinct from API providers) so the
router knows the free-pool ORDER and which are locally reachable vs. documented-only.

*This is the free-compute map. The deal-radar integrates it as compute-source classes — the router's
"free pool" beyond API free tiers. The three hidden-gold sources (Petals, Puter, WebLLM/Chrome) are
the ones closest to genuinely-unlimited $0 inference.*
