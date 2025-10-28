from __future__ import annotations

__all__ = ["normalize_pattern"]


def normalize_pattern(pattern: str) -> str:
    """Add wildcards if pattern lacks glob meta characters."""
    if not any(ch in pattern for ch in ["*", "?", "[", "]"]):
        return f"*{pattern}*"
    return pattern
