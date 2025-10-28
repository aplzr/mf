from __future__ import annotations

__all__ = ["normalize_pattern"]


def normalize_pattern(pattern: str) -> str:
    """Normalize a search pattern.

    Args:
        pattern (str): Raw pattern (may lack wildcards).

    Returns:
        str: Pattern wrapped with * on both sides if no glob characters found.
    """
    if not any(ch in pattern for ch in ["*", "?", "[", "]"]):
        return f"*{pattern}*"
    return pattern
