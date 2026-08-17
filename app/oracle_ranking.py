"""Oracle-1 Ranking with epistemically labeled scores.

Every score component needs:
- value: the score
- kind: MEASURED, DERIVED, ESTIMATED, HEURISTIC, PRIOR, UNKNOWN
- method: how it was computed
- confidence: how confident we are
"""
from __future__ import annotations

import json
from typing import Optional


class ScoreComponent:
    """A single score with provenance."""
    
    def __init__(self, value: float, kind: str, method: str, confidence: float):
        self.value = value
        self.kind = kind  # MEASURED, DERIVED, ESTIMATED, HEURISTIC, PRIOR, UNKNOWN
        self.method = method
        self.confidence = confidence
    
    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "kind": self.kind,
            "method": self.method,
            "confidence": self.confidence,
        }


class OracleRanking:
    """Ranking with epistemic labels."""
    
    def __init__(self):
        self.scores = {}
    
    def add_score(self, dimension: str, score: ScoreComponent):
        """Add a score for a dimension."""
        self.scores[dimension] = score
    
    def get_score(self, dimension: str) -> Optional[ScoreComponent]:
        """Get score for a dimension."""
        return self.scores.get(dimension)
    
    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.scores.items()}
    
    def get_confidence_summary(self) -> dict:
        """Get summary of confidence levels."""
        measured = sum(1 for s in self.scores.values() if s.kind == "MEASURED")
        estimated = sum(1 for s in self.scores.values() if s.kind == "ESTIMATED")
        heuristic = sum(1 for s in self.scores.values() if s.kind == "HEURISTIC")
        unknown = sum(1 for s in self.scores.values() if s.kind == "UNKNOWN")
        
        return {
            "measured": measured,
            "estimated": estimated,
            "heuristic": heuristic,
            "unknown": unknown,
            "total": len(self.scores),
        }


def rank_offer(offer: dict, task: str = None) -> OracleRanking:
    """Rank an offer with epistemic labels."""
    ranking = OracleRanking()
    
    # Price score
    input_per_m = offer.get("input_per_m")
    if input_per_m is not None:
        if input_per_m == 0:
            ranking.add_score("price", ScoreComponent(100.0, "MEASURED", "zero_price", 0.95))
        else:
            # Normalize: lower is better
            score = max(0, 100 - input_per_m * 100)
            ranking.add_score("price", ScoreComponent(score, "MEASURED", "price_measurement", 0.9))
    else:
        ranking.add_score("price", ScoreComponent(0.0, "UNKNOWN", "no_price_data", 0.0))
    
    # Free score
    free = offer.get("free")
    if free:
        ranking.add_score("free", ScoreComponent(100.0, "MEASURED", "free_flag", 0.95))
    else:
        ranking.add_score("free", ScoreComponent(0.0, "MEASURED", "not_free", 0.95))
    
    # Context score
    context = offer.get("context_tokens")
    if context is not None:
        # Normalize: 1M+ = 100, 128K = 50, etc.
        score = min(100, context / 10000)
        ranking.add_score("context", ScoreComponent(score, "MEASURED", "context_measurement", 0.9))
    else:
        ranking.add_score("context", ScoreComponent(0.0, "UNKNOWN", "no_context_data", 0.0))
    
    # Tool support (heuristic based on provider)
    provider = offer.get("provider_id", "")
    tool_providers = {"openai", "anthropic", "google", "openrouter"}
    if provider in tool_providers:
        ranking.add_score("tool_support", ScoreComponent(70.0, "HEURISTIC", "provider_heuristic", 0.4))
    else:
        ranking.add_score("tool_support", ScoreComponent(30.0, "HEURISTIC", "unknown_provider", 0.2))
    
    return ranking
