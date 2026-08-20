"""app/deal_comparison.py — Deal comparison and recommendation engine.

Analyzes deals and provides recommendations based on user preferences.
"""
from __future__ import annotations

import sys
import sqlite3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import canonical_db


@dataclass
class DealRecommendation:
    """A deal recommendation with reasoning."""
    model_id: str
    provider_id: str
    score: float
    reasons: list[str]
    trade_offs: list[str]
    best_for: str
    usage_multiplier: Optional[float] = None
    context_tokens: Optional[int] = None
    free: bool = False


def compare_deals(
    task: str = "coding",
    optimize_for: str = "value",  # value, speed, context, cost
    max_price: Optional[float] = None,
    require_tools: bool = False,
    min_context: Optional[int] = None,
) -> list[DealRecommendation]:
    """Compare deals and provide recommendations.
    
    Args:
        task: The task type (coding, chat, reasoning, etc.)
        optimize_for: What to optimize for (value, speed, context, cost)
        max_price: Maximum price per million tokens
        require_tools: Whether tool calling is required
        min_context: Minimum context window required
    
    Returns:
        List of DealRecommendation objects sorted by score
    """
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    # Get all active offers
    offers = conn.execute("""
        SELECT * FROM offers 
        WHERE lifecycle_state != 'SUPERSEDED'
        AND (free = 1 OR input_per_m IS NOT NULL)
    """).fetchall()
    
    recommendations = []
    
    for offer in offers:
        # Skip offers that don't meet requirements
        if max_price and offer['input_per_m'] and offer['input_per_m'] > max_price:
            continue
        if min_context and offer['context_tokens'] and offer['context_tokens'] < min_context:
            continue
        
        # Calculate score based on optimization criteria
        score, reasons, trade_offs = _calculate_score(
            offer, task, optimize_for, require_tools
        )
        
        if score > 0:
            recommendations.append(DealRecommendation(
                model_id=offer['model_id'],
                provider_id=offer['provider_id'],
                score=score,
                reasons=reasons,
                trade_offs=trade_offs,
                best_for=_determine_best_for(offer, task),
                usage_multiplier=offer['usage_multiplier'],
                context_tokens=offer['context_tokens'],
                free=bool(offer['free']),
            ))
    
    conn.close()
    
    # Sort by score (highest first)
    recommendations.sort(key=lambda r: r.score, reverse=True)
    
    return recommendations[:10]  # Return top 10


def _calculate_score(
    offer: dict,
    task: str,
    optimize_for: str,
    require_tools: bool,
) -> tuple[float, list[str], list[str]]:
    """Calculate a score for an offer based on criteria."""
    score = 0.0
    reasons = []
    trade_offs = []
    
    # Base score for free offers
    if offer['free']:
        score += 50
        reasons.append("Free tier available")
    
    # Usage multiplier bonus
    if offer['usage_multiplier'] and offer['usage_multiplier'] > 1:
        multiplier_bonus = min(offer['usage_multiplier'] * 10, 50)  # Cap at 50
        score += multiplier_bonus
        reasons.append(f"{offer['usage_multiplier']}x usage multiplier")
    
    # Context window bonus (cap at 30 points)
    if offer['context_tokens']:
        context_score = min(offer['context_tokens'] / 10000, 30)
        score += context_score
        reasons.append(f"{offer['context_tokens']//1000}K context window")
    
    # Price score (lower is better)
    if offer['input_per_m'] is not None:
        if offer['input_per_m'] == 0:
            score += 40
            reasons.append("Zero cost")
        elif offer['input_per_m'] > 0:
            # Inverse price score (lower price = higher score)
            # Cap at 40 points for very cheap models
            price_score = max(0, 40 - (offer['input_per_m'] * 2))
            score += price_score
            reasons.append(f"${offer['input_per_m']:.2f}/M tokens")
    
    # Task-specific bonuses
    if task == "coding":
        # Coding tasks benefit from larger context and tool support
        if offer['context_tokens'] and offer['context_tokens'] >= 64000:
            score += 20
            reasons.append("Large context for code")
    elif task == "chat":
        # Chat tasks benefit from speed and low cost
        if offer['free']:
            score += 15
            reasons.append("Free for chat")
    
    # Optimization-specific adjustments
    if optimize_for == "speed":
        # Prefer smaller, faster models
        if offer['context_tokens'] and offer['context_tokens'] < 32000:
            score += 15
            reasons.append("Smaller context = faster inference")
        else:
            trade_offs.append("Larger context may be slower")
    elif optimize_for == "context":
        # Prefer larger context
        if offer['context_tokens'] and offer['context_tokens'] >= 100000:
            score += 25
            reasons.append("Very large context window")
    elif optimize_for == "cost":
        # Prefer free or very cheap
        if offer['free']:
            score += 30
            reasons.append("Zero cost")
        elif offer['input_per_m'] and offer['input_per_m'] < 1:
            score += 20
            reasons.append("Very low cost")
    
    return score, reasons, trade_offs


def _determine_best_for(offer: dict, task: str) -> str:
    """Determine what this offer is best for."""
    if offer['free']:
        return "Prototyping, testing, low-volume usage"
    if offer['usage_multiplier'] and offer['usage_multiplier'] >= 8:
        return "High-volume usage with usage multiplier"
    if offer['context_tokens'] and offer['context_tokens'] >= 100000:
        return "Large codebases, complex reasoning"
    if offer['input_per_m'] and offer['input_per_m'] < 1:
        return "Cost-sensitive production workloads"
    return "General-purpose usage"


def get_deal_comparison(model1: str, model2: str) -> dict:
    """Compare two specific deals and provide detailed analysis."""
    conn = canonical_db.connect()
    canonical_db.migrate(conn)
    
    # Get both offers
    offer1 = conn.execute("""
        SELECT * FROM offers 
        WHERE model_id LIKE ?
        LIMIT 1
    """, (f"%{model1}%",)).fetchone()
    
    offer2 = conn.execute("""
        SELECT * FROM offers 
        WHERE model_id LIKE ?
        LIMIT 1
    """, (f"%{model2}%",)).fetchone()
    
    conn.close()
    
    if not offer1 or not offer2:
        return {"error": "One or both models not found"}
    
    comparison = {
        "model1": {
            "id": offer1['model_id'],
            "provider": offer1['provider_id'],
            "free": bool(offer1['free']),
            "price": offer1['input_per_m'],
            "context": offer1['context_tokens'],
            "multiplier": offer1['usage_multiplier'],
        },
        "model2": {
            "id": offer2['model_id'],
            "provider": offer2['provider_id'],
            "free": bool(offer2['free']),
            "price": offer2['input_per_m'],
            "context": offer2['context_tokens'],
            "multiplier": offer2['usage_multiplier'],
        },
        "recommendation": "",
        "reasoning": [],
    }
    
    # Compare and recommend
    score1, reasons1, _ = _calculate_score(offer1, "coding", "value", False)
    score2, reasons2, _ = _calculate_score(offer2, "coding", "value", False)
    
    if score1 > score2:
        comparison["recommendation"] = offer1['model_id']
        comparison["reasoning"] = reasons1
    elif score2 > score1:
        comparison["recommendation"] = offer2['model_id']
        comparison["reasoning"] = reasons2
    else:
        comparison["recommendation"] = "Either model"
        comparison["reasoning"] = ["Both models offer similar value"]
    
    return comparison


if __name__ == "__main__":
    # Test the comparison
    print("=== Deal Comparison Test ===\n")
    
    # Compare Hy3 vs MiMo-V2.5
    result = get_deal_comparison("hy3", "mimo-v2.5")
    print(f"Comparison: {result['model1']['id']} vs {result['model2']['id']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Reasoning: {result['reasoning']}")
    
    print("\n=== Top Deals for Coding ===\n")
    recommendations = compare_deals(task="coding", optimize_for="value")
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"{i}. {rec.model_id}")
        print(f"   Provider: {rec.provider_id}")
        print(f"   Score: {rec.score:.1f}")
        print(f"   Best for: {rec.best_for}")
        if rec.usage_multiplier:
            print(f"   Multiplier: {rec.usage_multiplier}x")
        print(f"   Reasons: {', '.join(rec.reasons)}")
        print()