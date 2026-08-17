"""Model identity resolution for LLM Deals."""
from .resolver import (
    normalize_model_name, infer_relationship, can_transfer_field,
    EXACT_SAME_MODEL, EXPLICIT_PROVIDER_ALIAS, SAME_MODEL_DIFFERENT_PROVIDER,
    SIBLING_VARIANT, MODEL_FAMILY, UNKNOWN_RELATION, FIELD_LOCALITY,
)
