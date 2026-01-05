"""Validation utilities.

Provides validation functions to ensure runtime requirements are met.

Validation Strategy:
    - Validates data structure and required fields
    - Exits with error if validation fails
    - Returns validated, typed data for use in operations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .console import print_and_raise, print_warn


def validate_search_paths(search_paths: list[str]) -> list[Path]:
    """Return existing configured search paths.

    Args:
        search_paths (list[str]): Search path strings to validate.

    Raises:
        typer.Exit: If no valid search paths are configured.

    Returns:
        list[Path]: List of validated existing search paths.
    """
    validated: list[Path] = []

    for search_path in search_paths:
        p = Path(search_path)

        if not p.exists():
            print_warn(f"Configured search path {search_path} does not exist.")
        else:
            validated.append(p)

    if not validated:
        print_and_raise(
            "List of search paths is empty or paths don't exist. "
            "Set search paths with 'mf config set search_paths'."
        )

    return validated


def validate_search_cache(cache_data: dict[str, Any]) -> dict[str, Any]:
    """Validate search cache structure has required keys.

    Args:
        cache_data: Raw cache data from JSON.

    Raises:
        KeyError: If required keys are missing.

    Returns:
        dict[str, Any]: The validated cache data.
    """
    required_keys = {"pattern", "results", "timestamp"}

    if missing := required_keys - cache_data.keys():
        raise KeyError(f"Cache missing required keys: {missing}")

    return cache_data
