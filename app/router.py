"""app/router.py — Hot Router: 3-stage LLM routing with quota shadow pricing.

Implements mechanisms from:
- FrugalGPT: confidence threshold cascade
- BaRP: lambda preference knob (one policy, all tradeoffs)
- SeqRoute: session budget tracking
- MixLLM: contextual bandit scoring
- UCCI: calibrated escalation
- Cluster/Route/Escalate: two-stage cascade

Core insight: "Minimize expected cost per successful task under dynamic
capability, latency, quota and market constraints."
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# --- Quota Shadow Pricing ---

@dataclass
class QuotaState:
    """Tracks remaining quota per provider with shadow pricing."""
    provider_id: str
    total_quota: int = 0
    remaining_quota: int = 0
    reset_at: float = 0  # unix timestamp
    usage_today: int = 0
    last_updated: float = 0
    # Credit tracking
    credits_remaining: float = 0
    credits_expires_at: float = 0

    def shadow_price(self) -> float:
        """Calculate shadow price for using one unit of this quota.

        High shadow price = quota is scarce, don't waste it.
        Low shadow price = quota is plentiful or expiring soon.

        From llmrouting.md:
        - If remaining quota is plentiful → shadow price ≈ $0
        - If remaining quota is scarce → shadow price high
        - If credits expire tonight → shadow price collapses → BURN THEM NOW
        """
        now = time.time()

        # If credits are expiring soon, shadow price → 0 (burn them)
        if self.credits_expires_at > 0:
            hours_until_expiry = (self.credits_expires_at - now) / 3600
            if hours_until_expiry < 2:
                return 0.0  # BURN THEM NOW
            elif hours_until_expiry < 24:
                # Credits expiring within 24h — discount shadow price
                return 0.1

        # If no quota info, assume moderate
        if self.total_quota == 0:
            return 0.5

        # Quota scarcity ratio
        remaining_ratio = self.remaining_quota / max(self.total_quota, 1)

        # Time pressure (hours until reset)
        hours_until_reset = max(0, (self.reset_at - now)) / 3600
        if hours_until_reset == 0:
            hours_until_reset = 24  # assume 24h if no reset time

        # Predicted demand (assume uniform usage)
        predicted_remaining_demand = self.usage_today * (hours_until_reset / 24)

        # Scarcity score: 0 = plenty, 1 = scarce
        if predicted_remaining_demand > 0:
            scarcity = 1.0 - min(1.0, self.remaining_quota / predicted_remaining_demand)
        else:
            scarcity = 1.0 - remaining_ratio

        # Shadow price scales with scarcity
        return max(0.0, min(1.0, scarcity))


def expected_cost(offer: dict, quota: QuotaState, task_tokens: int = 1000,
                  failure_prob: float = 0.1, escalation_cost: float = 0.0) -> float:
    """Calculate EXPECTED COST including shadow pricing.

    From llmrouting.md:
    EXPECTED COST = marginal token cost + shadow cost + failure×escalation + penalties
    """
    in_m = offer.get("input_per_m") or 0
    out_m = offer.get("output_per_m") or 0
    is_free = offer.get("free", False)

    # Marginal token cost
    if is_free:
        marginal = 0.0
    else:
        marginal = (in_m + out_m) * task_tokens / 1_000_000

    # Shadow cost for using quota
    shadow = quota.shadow_price() * 0.01  # normalize to $ scale

    # Failure + escalation risk
    escalation_risk = failure_prob * escalation_cost

    return marginal + shadow + escalation_risk


# --- The 3-Stage Router ---

# Task classification keywords (from Semantic Router pattern)
TASK_KEYWORDS = {
    "coding": ["code", "function", "implement", "debug", "refactor", "class", "method", "bug", "fix", "test", "compile", "python", "javascript", "typescript", "rust"],
    "agentic": ["agent", "tool", "function call", "api", "autonomous", "multi-step", "plan", "execute", "verify"],
    "extraction": ["extract", "parse", "format", "convert", "transform", "json", "csv", "structured"],
    "research": ["research", "analyze", "compare", "evaluate", "synthesize", "review", "literature"],
    "reasoning": ["why", "explain", "reason", "logic", "proof", "argument", "deduce", "infer"],
    "creative": ["write", "story", "creative", "poem", "narrative", "imagine", "fiction"],
    "summarize": ["summarize", "summary", "tldr", "brief", "overview", "condense"],
    "translation": ["translate", "translation", "language", "localize"],
    "vision": ["image", "picture", "photo", "screenshot", "diagram", "visual", "describe this image"],
}


def classify_task(query: str) -> str:
    """Classify a query into a task type using keyword matching.

    In production, replace with Semantic Router (semantic-router.readthedocs.io)
    for vector-similarity-based classification without LLM overhead.
    """
    query_lower = query.lower()
    scores = {}
    for task, keywords in TASK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scores[task] = score

    if scores:
        return max(scores, key=scores.get)
    return "general"


def estimate_difficulty(query: str, task: str) -> float:
    """Estimate query difficulty (0=easy, 1=hard).

    From Hybrid LLM: difficulty estimation via complexity signals.
    Simple heuristics (in production, use a trained classifier).
    """
    difficulty = 0.3  # baseline

    # Length signal
    if len(query) > 2000:
        difficulty += 0.2
    elif len(query) > 500:
        difficulty += 0.1

    # Task-specific signals
    if task == "coding":
        if any(w in query.lower() for w in ["algorithm", "optimize", "concurrent", "parallel", "architecture"]):
            difficulty += 0.3
        if "debug" in query.lower() or "error" in query.lower():
            difficulty += 0.1
    elif task == "reasoning":
        difficulty += 0.2
    elif task == "agentic":
        if "multi-step" in query.lower() or "plan" in query.lower():
            difficulty += 0.2
    elif task == "creative":
        difficulty += 0.15

    # Code presence
    if "```" in query or "def " in query or "class " in query:
        difficulty += 0.1

    return min(1.0, difficulty)


# --- Lambda Preference (BaRP-style) ---

def compute_routing_score(quality: float, cost: float, latency_ms: float,
                          reliability: float, lambda_val: float = 0.5) -> float:
    """Compute routing score with lambda preference knob.

    From BaRP:
    r = w_q * quality - w_c * cost_normalized

    lambda=0: maximize quality (cost-blind)
    lambda=1: minimize cost (quality-blind)
    lambda=0.5: balanced
    """
    # Normalize cost to [0,1] (assume $0-10 range)
    cost_norm = min(1.0, cost / 10.0)

    # Latency penalty (from MixLLM)
    latency_penalty = max(0, (latency_ms - 3000) / 10000)  # penalty above 3s

    # Score: quality-weighted minus cost-weighted
    score = (1 - lambda_val) * quality - lambda_val * cost_norm - 0.1 * latency_penalty + 0.1 * reliability

    return score


# --- Cascade / Confidence Escalation (FrugalGPT + UCCI) ---

def should_escalate(confidence: float, threshold: float = 0.7) -> bool:
    """Decide whether to escalate to a stronger model.

    From UCCI: escalate if Pr(error) > theta
    Simplified: escalate if confidence < threshold.
    """
    return confidence < threshold


def cascade_select(candidates: list[dict], query: str, task: str,
                   quality_floor: float = 0.7, lambda_val: float = 0.5,
                   budget: float = None) -> dict:
    """Select model via cascade: cheapest first, escalate if needed.

    From FrugalGPT: try cheap → check confidence → escalate if low.

    In our implementation, we predict confidence from task/difficulty
    rather than running a separate scoring model.
    """
    difficulty = estimate_difficulty(query, task)

    # Sort by cost (cheapest first)
    sorted_candidates = sorted(candidates, key=lambda c: c.get("input_per_m") or 0)

    for candidate in sorted_candidates:
        # Predict success probability based on capability vs difficulty
        vec = candidate.get("vector", {})
        capability = vec.get("intelligence", 50) / 100.0
        task_fit = vec.get(task, 50) / 100.0 if task in vec else capability

        # Confidence = capability adjusted for difficulty
        confidence = task_fit * (1 - difficulty * 0.5)

        # Check budget
        if budget is not None:
            cost = candidate.get("effective_costs", {}).get(f"{task}_task", {}).get("effective_cost_per_task", 0)
            if cost > budget:
                continue

        # Check quality floor
        if confidence >= quality_floor:
            return {
                "model": candidate,
                "confidence": round(confidence, 3),
                "escalated": False,
                "difficulty": round(difficulty, 3),
            }

    # Fallback to best available
    if sorted_candidates:
        best = max(sorted_candidates, key=lambda c: c.get("vector", {}).get("intelligence", 0))
        return {
            "model": best,
            "confidence": 0.5,
            "escalated": True,
            "difficulty": round(difficulty, 3),
            "note": "All candidates below quality floor, escalated to strongest",
        }

    return {"model": None, "confidence": 0, "escalated": False, "note": "No candidates"}


# --- Session Budget Tracker (SeqRoute-style) ---

@dataclass
class SessionBudget:
    """Track budget across a multi-turn session."""
    total_budget: float = 1.0  # normalized
    remaining: float = 1.0
    spent: float = 0
    turn_count: int = 0
    history: list = field(default_factory=list)

    def __post_init__(self):
        self.remaining = self.total_budget

    def spend(self, cost: float) -> bool:
        """Spend budget. Returns False if bankrupt."""
        if self.remaining <= 0:
            return False
        self.remaining = max(0, self.remaining - cost / self.total_budget)
        self.spent += cost
        self.turn_count += 1
        self.history.append({"turn": self.turn_count, "cost": cost, "remaining": self.remaining})
        return True

    def is_bankrupt(self) -> bool:
        return self.remaining <= 0

    def urgency(self) -> float:
        """How urgent is it to save budget? 0=plenty, 1=almost bankrupt."""
        return 1.0 - self.remaining


# --- The Full Hot Router ---

class HotRouter:
    """3-stage router: Task → Model → Provider.

    Combines:
- Task classification (keyword-based, upgradeable to Semantic Router)
- Model scoring (10D vector from scoring.py)
- Provider selection (quota shadow pricing + deal awareness)
- Cascade escalation (FrugalGPT/UCCI)
- Lambda preference (BaRP)
- Session budget tracking (SeqRoute)
    """

    def __init__(self, offers: list[dict], lambda_val: float = 0.5,
                 quality_floor: float = 0.7, budget: float = None):
        self.offers = offers
        self.lambda_val = lambda_val
        self.quality_floor = quality_floor
        self.budget = budget
        self.quota_states: dict[str, QuotaState] = {}
        self.session = SessionBudget(total_budget=budget if budget else 1.0)

    def update_quota(self, provider_id: str, total: int, remaining: int,
                     reset_at: float, credits: float = 0, credits_expires: float = 0):
        """Update quota state for a provider."""
        self.quota_states[provider_id] = QuotaState(
            provider_id=provider_id,
            total_quota=total,
            remaining_quota=remaining,
            reset_at=reset_at,
            usage_today=total - remaining,
            last_updated=time.time(),
            credits_remaining=credits,
            credits_expires_at=credits_expires,
        )

    def route(self, query: str, model_preference: str = None,
              role: str = None, task: str = None) -> dict:
        """Route a query through the 3-stage pipeline.

        Returns: model, provider, why, cost estimate, escalation info.
        """
        # Stage 1: Task classification
        if task is None:
            task = classify_task(query)
        difficulty = estimate_difficulty(query, task)

        # Stage 2: Model selection
        import scoring
        scored = [scoring.score_and_badge(o) for o in self.offers]

        # Filter by role if specified
        if role == "worker":
            scored = [s for s in scored if "worker" in (s.get("badges") or [])]
        elif role == "planner":
            scored = [s for s in scored if s["vector"]["intelligence"] >= 70]
        elif role == "reviewer":
            scored = [s for s in scored if s["vector"]["intelligence"] >= 75]

        # Filter by tool calling if agentic task
        if task in ("agentic", "coding"):
            tool_capable = [s for s in scored if s["vector"]["tool_calling"] >= 60]
            if tool_capable:
                scored = tool_capable

        if not scored:
            return {"error": "No suitable models", "task": task}

        # Score each candidate with lambda preference
        for s in scored:
            vec = s["vector"]
            # Task-specific quality
            task_quality = vec.get(task, vec["intelligence"]) / 100.0
            # Cost
            cost_data = s.get("effective_costs", {}).get(f"{task}_task", {})
            cost = cost_data.get("effective_cost_per_task", 0)
            # Latency (from metadata)
            latency = 500  # default
            # Reliability
            reliability = vec["reliability"] / 100.0

            s["_routing_score"] = compute_routing_score(
                task_quality, cost, latency, reliability, self.lambda_val)

        # Sort by routing score
        scored.sort(key=lambda x: x.get("_routing_score", 0), reverse=True)

        # Stage 3: Provider selection with quota awareness
        best = scored[0]
        provider = best.get("provider_id", "unknown")

        # Check quota shadow pricing
        quota = self.quota_states.get(provider)
        if quota:
            shadow = quota.shadow_price()
            if shadow > 0.8:
                # Quota is scarce — try next provider
                for s in scored[1:]:
                    alt_provider = s.get("provider_id", "")
                    alt_quota = self.quota_states.get(alt_provider)
                    if not alt_quota or alt_quota.shadow_price() < 0.5:
                        best = s
                        provider = alt_provider
                        break

        # Cascade check
        difficulty = estimate_difficulty(query, task)
        capability = best["vector"].get("intelligence", 50) / 100.0
        confidence = capability * (1 - difficulty * 0.5)

        escalated = False
        if confidence < self.quality_floor:
            # Escalate to strongest available
            strongest = max(scored, key=lambda s: s["vector"]["intelligence"])
            if strongest != best:
                best = strongest
                provider = strongest.get("provider_id", "unknown")
                escalated = True

        # Session budget check
        cost = best.get("effective_costs", {}).get(f"{task}_task", {}).get("effective_cost_per_task", 0)
        if self.budget and not self.session.spend(cost):
            return {"error": "Session budget exhausted", "task": task, "spent": self.session.spent}

        return {
            "model": best.get("model_id"),
            "provider": provider,
            "task": task,
            "difficulty": round(difficulty, 3),
            "confidence": round(confidence, 3),
            "escalated": escalated,
            "routing_score": round(best.get("_routing_score", 0), 3),
            "badges": best.get("badges", []),
            "vector": best["vector"],
            "effective_cost": cost,
            "lambda": self.lambda_val,
            "session_remaining": self.session.remaining,
            "why": self._explain(best, task, escalated),
        }

    def _explain(self, offer: dict, task: str, escalated: bool) -> list[str]:
        reasons = []
        vec = offer["vector"]
        badges = offer.get("badges", [])

        if escalated:
            reasons.append("escalated from cheaper model (low confidence)")
        if "workhorse" in badges:
            reasons.append("excellent workhorse for this task")
        if "fast" in badges:
            reasons.append("fast inference")
        if offer.get("free"):
            reasons.append("free to use")
        if vec["value"] >= 80:
            reasons.append("exceptional value")
        if self.lambda_val < 0.3:
            reasons.append("quality-prioritized routing")
        elif self.lambda_val > 0.7:
            reasons.append("cost-prioritized routing")

        return reasons[:4]
