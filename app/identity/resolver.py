"""Model identity resolution.

Maps provider-specific model identifiers to canonical model identity.
Uses identity relationships:
  EXACT_SAME_MODEL
  EXPLICIT_PROVIDER_ALIAS
  SAME_MODEL_DIFFERENT_PROVIDER
  SIBLING_VARIANT
  MODEL_FAMILY
  UNKNOWN_RELATION
"""
from __future__ import annotations

import re
from typing import Optional


# Identity relationship types
EXACT_SAME_MODEL = "EXACT_SAME_MODEL"
EXPLICIT_PROVIDER_ALIAS = "EXPLICIT_PROVIDER_ALIAS"
SAME_MODEL_DIFFERENT_PROVIDER = "SAME_MODEL_DIFFERENT_PROVIDER"
SIBLING_VARIANT = "SIBLING_VARIANT"
MODEL_FAMILY = "MODEL_FAMILY"
UNKNOWN_RELATION = "UNKNOWN_RELATION"

# Fields that can propagate across EXACT_SAME_MODEL only
EXACT_ONLY_FIELDS = {"benchmark_scores", "native_modality", "release_date"}

# Fields that NEVER propagate across providers
NEVER_PROPAGATE = {
    "provider_price", "provider_quota", "provider_latency",
    "provider_tool_support", "promotion_multiplier", "region",
    "subscription_allowance", "free_quota", "rate_limit",
}


def normalize_model_name(name: str) -> str:
    """Normalize a model name for fuzzy matching."""
    if not name:
        return ""
    # Remove provider prefix
    base = name.split("/")[-1] if "/" in name else name
    # Remove version suffixes
    base = re.sub(r"[-_]?(v\d+|pro|ultraspeed|flash|omni|reasoning|non-reasoning|0\d{3})", "", base, flags=re.IGNORECASE)
    return base.strip("-_").lower()


def infer_relationship(left: str, right: str) -> str:
    """Infer identity relationship between two model names."""
    left_norm = normalize_model_name(left)
    right_norm = normalize_model_name(right)

    if left_norm == right_norm:
        # Same normalized name — could be EXACT or SIBLING
        # Need to check if they're actually the same model
        if left.lower() == right.lower():
            return EXACT_SAME_MODEL
        # Same family, different variants
        return SIBLING_VARIANT

    # Check if one is a prefix of the other
    if left_norm.startswith(right_norm) or right_norm.startswith(left_norm):
        return MODEL_FAMILY

    return UNKNOWN_RELATION


# Field-locality matrix: which fields can be transferred across relationships
FIELD_LOCALITY = {
    "canonical_name": {EXACT_SAME_MODEL, EXPLICIT_PROVIDER_ALIAS, SAME_MODEL_DIFFERENT_PROVIDER},
    "release_date": {EXACT_SAME_MODEL},
    "benchmark_scores": {EXACT_SAME_MODEL},  # NEVER SIBLING
    "native_modality": {EXACT_SAME_MODEL},
    "native_max_context": {EXACT_SAME_MODEL, SAME_MODEL_DIFFERENT_PROVIDER},  # maybe with evidence
    "provider_price": set(),  # NEVER cross-provider
    "provider_quota": set(),
    "tool_support": set(),  # NEVER blindly
    "openai_compatible": set(),
    "latency": set(),
    "region": set(),
}


def can_transfer_field(field: str, relationship: str) -> bool:
    """Check if a field can be transferred across this relationship."""
    allowed = FIELD_LOCALITY.get(field, set())
    return relationship in allowed
