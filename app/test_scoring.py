#!/usr/bin/env python3
"""Test scoring against research-backed expectations."""
import sys
sys.path.insert(0, 'app')

from scoring import score_vector, derive_badges, score_and_badge


def test_scoring_research_alignment():
    """Verify scoring aligns with research."""
    print("Testing scoring research alignment...")
    
    # Test 1: Free model should have high cost_score
    free_offer = {"free": True, "input_per_m": 0}
    vector = score_vector(free_offer)
    assert vector["cost_score"] == 100, "Free model should have cost_score=100"
    print("  PASS: Free model cost_score")
    
    # Test 2: Expensive model should have low cost_score
    expensive_offer = {"free": False, "input_per_m": 10.0}
    vector = score_vector(expensive_offer)
    assert vector["cost_score"] < 50, "Expensive model should have low cost_score"
    print("  PASS: Expensive model cost_score")
    
    # Test 3: High context should have high context_score
    ctx_offer = {"context_tokens": 1000000}
    vector = score_vector(ctx_offer)
    assert vector["context_score"] == 100, "1M context should have context_score=100"
    print("  PASS: High context score")
    
    # Test 4: Value calculation
    intel_offer = {"free": True, "metadata": {"benchmarks": [{"name": "SWE-Bench", "score": 80}]}}
    vector = score_vector(intel_offer)
    assert vector["value"] == 80, "Free + intelligence=80 should have value=80"
    print("  PASS: Value calculation")
    
    # Test 5: Badge derivation
    offer = {"free": True, "metadata": {"benchmarks": [{"name": "SWE-Bench", "score": 85}]}}
    result = score_and_badge(offer)
    assert "free" in result["badges"], "Free model should have free badge"
    assert "frontier" in result["badges"], "Intelligence≥80 should have frontier badge"
    print("  PASS: Badge derivation")
    
    print("\nAll scoring tests passed!")
    return True


if __name__ == "__main__":
    test_scoring_research_alignment()
