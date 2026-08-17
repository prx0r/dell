"""app/providers.py — Provider metadata: setup difficulty, T&C, instructions, rate limits.

The full aggregator data for each LLM inference provider. This is the "CoinGecko" layer —
not just prices, but HOW to get the deal, how hard it is, what you get, and the fine print.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderMeta:
    provider_id: str
    name: str
    homepage: str
    signup_url: str
    api_docs_url: str
    # Setup difficulty (1=easy auto, 2=account+key, 3=approval, 4=enterprise)
    setup_difficulty: int
    setup_steps: list[str] = field(default_factory=list)
    # What you get
    free_tier: str = ""  # description of free tier
    free_requests_day: int | None = None
    free_requests_minute: int | None = None
    free_tokens_day: int | None = None
    context_window_max: int | None = None
    # Rate limits
    rate_limit_notes: str = ""
    # T&C highlights
    tos_url: str = ""
    tos_highlights: list[str] = field(default_factory=list)
    # Quality signals
    has_batch_api: bool = False
    has_structured_output: bool = False
    has_tool_calling: bool = False
    has_vision: bool = False
    has_reasoning: bool = False
    # Latency/throughput
    avg_latency_ms: float | None = None
    avg_throughput_tps: float | None = None
    # Agentic suitability
    agentic_notes: str = ""  # how good for agents
    # Metadata
    api_type: str = "openai"  # openai, anthropic, custom
    auth_method: str = "api_key"  # api_key, oauth, token
    pricing_model: str = "metered"  # metered, subscription, freemium, credit_pack


PROVIDERS: dict[str, ProviderMeta] = {
    "openrouter": ProviderMeta(
        provider_id="openrouter",
        name="OpenRouter",
        homepage="https://openrouter.ai",
        signup_url="https://openrouter.ai/keys",
        api_docs_url="https://openrouter.ai/docs",
        setup_difficulty=1,
        setup_steps=[
            "Go to openrouter.ai/keys",
            "Sign in with Google/GitHub",
            "Create API key",
            "Use base_url: https://openrouter.ai/api/v1",
        ],
        free_tier="Many :free models, no signup required for public models",
        free_requests_day=200,
        free_requests_minute=20,
        context_window_max=200000,
        rate_limit_notes="Free: 20 RPM, 50 RPD. Paid: varies by model.",
        tos_highlights=["No rate limit on paid models", "Model availability varies"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        has_batch_api=False,
        avg_latency_ms=800,
        agentic_notes="Best hub — one key, 300+ models. Free models great for testing.",
        pricing_model="freemium",
    ),
    "opencode-go": ProviderMeta(
        provider_id="opencode-go",
        name="OpenCode Go",
        homepage="https://dev.opencode.ai/go",
        signup_url="https://dev.opencode.ai/go",
        api_docs_url="https://opencode.ai/docs",
        setup_difficulty=1,
        setup_steps=[
            "Go to dev.opencode.ai/go",
            "Sign up",
            "Get API key",
            "Use base_url: https://opencode.ai/zen/go/v1",
        ],
        free_tier="Free tier with usage multipliers on subscribe",
        context_window_max=200000,
        tos_highlights=["Usage-based pricing", "Subscription gets 2x-5x multiplier"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        agentic_notes="Good for agents — OpenCode-native, competitive pricing.",
        pricing_model="freemium",
    ),
    "nous-portal": ProviderMeta(
        provider_id="nous-portal",
        name="Nous Portal",
        homepage="https://portal.nousresearch.com",
        signup_url="https://portal.nousresearch.com",
        api_docs_url="https://portal.nousresearch.com/docs",
        setup_difficulty=2,
        setup_steps=[
            "Go to portal.nousresearch.com",
            "Create account",
            "Subscribe to a plan (Hermes tier recommended)",
            "Get API key from dashboard",
            "Use base_url: https://portal.nousresearch.com/v1",
        ],
        free_tier="Limited free credits on signup",
        tos_highlights=["Subscription plans with model access", "Usage limits per plan"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        agentic_notes="Best Hermes models. Subscription gives access to all tiers.",
        pricing_model="subscription",
    ),
    "deepseek": ProviderMeta(
        provider_id="deepseek",
        name="DeepSeek",
        homepage="https://platform.deepseek.com",
        signup_url="https://platform.deepseek.com/api_keys",
        api_docs_url="https://platform.deepseek.com/api-docs",
        setup_difficulty=1,
        setup_steps=[
            "Go to platform.deepseek.com",
            "Sign up with email/phone (China phone works)",
            "Top up balance (min ¥10)",
            "Create API key",
            "Use base_url: https://api.deepseek.com/v1",
        ],
        free_tier="¥10 free credit on signup",
        free_requests_day=1000,
        context_window_max=128000,
        rate_limit_notes="RPM varies by tier. Off-peak discounts available.",
        tos_highlights=["Off-peak pricing 50% off", "Credit-based billing"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=False,
        has_reasoning=True,
        avg_latency_ms=600,
        agentic_notes="Best price-to-quality ratio. Off-peak is unbeatable for batch work.",
        pricing_model="credit_pack",
    ),
    "groq": ProviderMeta(
        provider_id="groq",
        name="Groq",
        homepage="https://groq.com",
        signup_url="https://console.groq.com/keys",
        api_docs_url="https://console.groq.com/docs",
        setup_difficulty=1,
        setup_steps=[
            "Go to console.groq.com",
            "Sign in with Google/GitHub",
            "Create API key",
            "Use base_url: https://api.groq.com/openai/v1",
        ],
        free_tier="Free tier: 30 RPM, 1000 RPD, 100K TPD",
        free_requests_day=1000,
        free_requests_minute=30,
        free_tokens_day=100000,
        context_window_max=131072,
        rate_limit_notes="Free: 30 RPM, 1000 RPD. Paid: higher limits.",
        tos_highlights=["Free tier generous for individual use", "Rate limited"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=False,
        avg_latency_ms=200,
        agentic_notes="FASTEST inference. Free tier great for prototyping.",
        pricing_model="freemium",
    ),
    "cerebras": ProviderMeta(
        provider_id="cerebras",
        name="Cerebras",
        homepage="https://cerebras.ai",
        signup_url="https://cloud.cerebras.ai",
        api_docs_url="https://cloud.cerebras.ai/docs",
        setup_difficulty=1,
        setup_steps=[
            "Go to cloud.cerebras.ai",
            "Sign up",
            "Create API key",
            "Use base_url: https://api.cerebras.ai/v1",
        ],
        free_tier="Free tier available",
        context_window_max=131072,
        has_tool_calling=True,
        has_structured_output=True,
        avg_latency_ms=150,
        agentic_notes="Incredibly fast inference. Good for real-time agents.",
        pricing_model="freemium",
    ),
    "cloudflare": ProviderMeta(
        provider_id="cloudflare",
        name="Cloudflare Workers AI",
        homepage="https://developers.cloudflare.com/workers-ai",
        signup_url="https://dash.cloudflare.com/sign-up",
        api_docs_url="https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility",
        setup_difficulty=2,
        setup_steps=[
            "Sign up at dash.cloudflare.com",
            "Go to Workers & Pages > AI",
            "Get API token",
            "Use base_url: https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        ],
        free_tier="10K free neurons/day on free plan",
        rate_limit_notes="Free: limited by neurons. Paid: pay-per-use.",
        tos_highlights=["Serverless pricing", "No egress fees"],
        has_tool_calling=False,
        has_structured_output=False,
        has_vision=True,
        agentic_notes="Good for edge inference. Free tier is real.",
        pricing_model="freemium",
    ),
    "together": ProviderMeta(
        provider_id="together",
        name="Together AI",
        homepage="https://together.ai",
        signup_url="https://api.together.xyz/settings/api-keys",
        api_docs_url="https://docs.together.ai",
        setup_difficulty=1,
        setup_steps=[
            "Go to together.ai",
            "Sign up",
            "Create API key",
            "Use base_url: https://api.together.xyz/v1",
        ],
        free_tier="$1 free credit on signup",
        context_window_max=200000,
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        agentic_notes="Great model selection. Good for open-source models.",
        pricing_model="credit_pack",
    ),
    "fireworks": ProviderMeta(
        provider_id="fireworks",
        name="Fireworks AI",
        homepage="https://fireworks.ai",
        signup_url="https://fireworks.ai/account/api-keys",
        api_docs_url="https://docs.fireworks.ai",
        setup_difficulty=1,
        setup_steps=[
            "Go to fireworks.ai",
            "Sign up",
            "Create API key",
            "Use base_url: https://api.fireworks.ai/inference/v1",
        ],
        free_tier="$1 free credit on signup",
        context_window_max=131072,
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=False,
        avg_latency_ms=300,
        agentic_notes="Fast inference, good open-source model selection.",
        pricing_model="credit_pack",
    ),
    "deepinfra": ProviderMeta(
        provider_id="deepinfra",
        name="DeepInfra",
        homepage="https://deepinfra.com",
        signup_url="https://deepinfra.com/dash/api_keys",
        api_docs_url="https://deepinfra.com/docs",
        setup_difficulty=1,
        setup_steps=[
            "Go to deepinfra.com",
            "Sign up",
            "Create API key",
            "Use base_url: https://api.deepinfra.com/v1/openai",
        ],
        free_tier="$1 free credit on signup",
        context_window_max=200000,
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        agentic_notes="Cheapest per-token for many models. Good for batch work.",
        pricing_model="credit_pack",
    ),
    "mistral": ProviderMeta(
        provider_id="mistral",
        name="Mistral AI",
        homepage="https://mistral.ai",
        signup_url="https://console.mistral.ai/api-keys/",
        api_docs_url="https://docs.mistral.ai",
        setup_difficulty=1,
        setup_steps=[
            "Go to console.mistral.ai",
            "Sign up",
            "Create API key",
            "Use base_url: https://api.mistral.ai/v1",
        ],
        free_tier="Free tier on La Plateforme",
        context_window_max=128000,
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        agentic_notes="Strong European provider. Good for compliance-sensitive work.",
        pricing_model="freemium",
    ),
    "google": ProviderMeta(
        provider_id="google",
        name="Google AI (Gemini)",
        homepage="https://ai.google.dev",
        signup_url="https://aistudio.google.com/apikey",
        api_docs_url="https://ai.google.dev/docs",
        setup_difficulty=1,
        setup_steps=[
            "Go to aistudio.google.com",
            "Sign in with Google",
            "Create API key",
            "Use: generativelanguage.googleapis.com/v1beta",
        ],
        free_tier="Generous free tier (RPM/RPD limits vary by model)",
        free_requests_day=1500,
        free_requests_minute=15,
        context_window_max=1000000,
        rate_limit_notes="Free: varies by model. Paid: higher.",
        tos_highlights=["Free tier is genuine", "Rate limits per model"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        agentic_notes="Largest context window. Free tier is best for long-context work.",
        pricing_model="freemium",
    ),
    "anthropic": ProviderMeta(
        provider_id="anthropic",
        name="Anthropic",
        homepage="https://anthropic.com",
        signup_url="https://console.anthropic.com/settings/keys",
        api_docs_url="https://docs.anthropic.com",
        setup_difficulty=2,
        setup_steps=[
            "Go to console.anthropic.com",
            "Sign up with email",
            "Verify phone number",
            "Add payment method (required even for free credits)",
            "Create API key",
        ],
        free_tier="$5 free credit on signup",
        context_window_max=200000,
        tos_highlights=["Usage-based pricing", "No free tier without payment method"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        has_batch_api=True,
        agentic_notes="Best for complex reasoning. Batch API saves 50%.",
        pricing_model="credit_pack",
    ),
    "openai": ProviderMeta(
        provider_id="openai",
        name="OpenAI",
        homepage="https://openai.com",
        signup_url="https://platform.openai.com/api-keys",
        api_docs_url="https://platform.openai.com/docs",
        setup_difficulty=2,
        setup_steps=[
            "Go to platform.openai.com",
            "Sign up with email",
            "Verify phone",
            "Add payment method (required)",
            "Create API key",
        ],
        free_tier="$5 free credit on signup (limited time)",
        context_window_max=128000,
        tos_highlights=["Usage-based pricing", "Credits expire"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        has_batch_api=True,
        agentic_notes="Industry standard. Batch API for 50% off.",
        pricing_model="credit_pack",
    ),
    "huggingface": ProviderMeta(
        provider_id="huggingface",
        name="HuggingFace Inference",
        homepage="https://huggingface.co/inference",
        signup_url="https://huggingface.co/settings/tokens",
        api_docs_url="https://huggingface.co/docs/inferenced/providers",
        setup_difficulty=1,
        setup_steps=[
            "Go to huggingface.co",
            "Sign up",
            "Go to Settings > Access Tokens",
            "Create token with 'inference.serverless.write' scope",
            "Use base_url: https://router.huggingface.co/v1",
        ],
        free_tier="$0.10/mo free credits, $2/mo PRO plan",
        context_window_max=200000,
        tos_highlights=["Per-provider pricing", "Auto-failover between providers"],
        has_tool_calling=True,
        has_structured_output=True,
        has_vision=True,
        has_reasoning=True,
        agentic_notes="BEST single add — one key, hundreds of models, per-provider pricing. Effectively a free OpenRouter.",
        pricing_model="freemium",
    ),
}

def get_provider(provider_id: str):
    return PROVIDERS.get(provider_id)

def get_all_providers():
    return list(PROVIDERS.values())

def get_easy_providers(max_difficulty: int = 1):
    return [p for p in PROVIDERS.values() if p.setup_difficulty <= max_difficulty]

def get_free_providers():
    return [p for p in PROVIDERS.values() if p.free_tier]

def get_agentic_providers():
    return [p for p in PROVIDERS.values()
            if p.setup_difficulty <= 2 and p.avg_latency_ms and p.avg_latency_ms < 1000]

def to_dict(p: ProviderMeta) -> dict:
    return {
        "provider_id": p.provider_id,
        "name": p.name,
        "homepage": p.homepage,
        "signup_url": p.signup_url,
        "api_docs_url": p.api_docs_url,
        "setup_difficulty": p.setup_difficulty,
        "setup_steps": p.setup_steps,
        "free_tier": p.free_tier,
        "free_requests_day": p.free_requests_day,
        "free_requests_minute": p.free_requests_minute,
        "free_tokens_day": p.free_tokens_day,
        "context_window_max": p.context_window_max,
        "rate_limit_notes": p.rate_limit_notes,
        "tos_highlights": p.tos_highlights,
        "has_batch_api": p.has_batch_api,
        "has_structured_output": p.has_structured_output,
        "has_tool_calling": p.has_tool_calling,
        "has_vision": p.has_vision,
        "has_reasoning": p.has_reasoning,
        "avg_latency_ms": p.avg_latency_ms,
        "avg_throughput_tps": p.avg_throughput_tps,
        "agentic_notes": p.agentic_notes,
        "api_type": p.api_type,
        "auth_method": p.auth_method,
        "pricing_model": p.pricing_model,
    }
