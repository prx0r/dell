"""Unknown Policy — Handle unknown values correctly.

Core principle: unknown cannot satisfy hard constraints.
"""
from __future__ import annotations

from enum import Enum


class UnknownPolicy(Enum):
    """How to handle unknown values."""
    EXCLUDE = "exclude"  # Unknown = ineligible for hard constraints
    ALLOW_WITH_WARNING = "allow_with_warning"  # Unknown allowed but flagged
    INCLUDE = "include"  # Unknown treated as potentially valid


def check_constraint(value, constraint, policy: UnknownPolicy = UnknownPolicy.EXCLUDE) -> dict:
    """Check if a value satisfies a constraint.
    
    Returns:
        {
            "satisfied": bool,
            "reason": str,
            "unknown_handled": bool
        }
    """
    if value is None:
        if policy == UnknownPolicy.EXCLUDE:
            return {"satisfied": False, "reason": "UNKNOWN", "unknown_handled": True}
        elif policy == UnknownPolicy.ALLOW_WITH_WARNING:
            return {"satisfied": True, "reason": "UNKNOWN_ALLOWED", "unknown_handled": True}
        else:
            return {"satisfied": True, "reason": "UNKNOWN_INCLUDED", "unknown_handled": False}
    
    # Value is known, check constraint
    if constraint is None:
        return {"satisfied": True, "reason": "NO_CONSTRAINT", "unknown_handled": False}
    
    # Check constraint type
    if isinstance(constraint, dict):
        if "min" in constraint and value < constraint["min"]:
            return {"satisfied": False, "reason": "BELOW_MIN", "unknown_handled": False}
        if "max" in constraint and value > constraint["max"]:
            return {"satisfied": False, "reason": "ABOVE_MAX", "unknown_handled": False}
    elif isinstance(constraint, bool):
        if constraint and not value:
            return {"satisfied": False, "reason": "REQUIRED_NOT_MET", "unknown_handled": False}
        if not constraint and value:
            return {"satisfied": False, "reason": "FORBIDDEN_BUT_PRESENT", "unknown_handled": False}
    
    return {"satisfied": True, "reason": "CONSTRAINT_MET", "unknown_handled": False}
