"""Validation utilities.

Provides validation functions to ensure runtime requirements are met.

Validation Strategy:
    - Validates data structure and required fields
    - Exits with error if validation fails
    - Returns validated, typed data for use in operations
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

from .console import print_and_raise, print_warn


def validate_search_paths(search_paths: list[Path]) -> list[Path]:
    """Return existing configured search paths.

    Args:
        search_paths (list[Path]): Search path strings to validate.

    Raises:
        typer.Exit: If no valid search paths are configured.

    Returns:
        list[Path]: List of validated existing search paths.
    """
    validated: list[Path] = []

    for search_path in search_paths:
        if not search_path.exists():
            print_warn(f"Configured search path {search_path} does not exist.")
        else:
            validated.append(search_path)

    if not validated:
        print_and_raise(
            "List of search paths is empty or paths don't exist. "
            "Set search paths with 'mf config set search_paths'."
        )

    return validated


def validate_search_paths_overlap(path_strings: list[str]) -> None:
    """Check if search paths are overlapping.

    Search paths are scanned recursively, so overlapping paths constitute a
    misconfiguration.

    Args:
        path_strings (list[str]): List of search paths.

    Raises:
        ValueError: Search paths overlap.

    Example:
        >>> validate_search_paths_overlap(["/media", "/media/videos"])
        ValueError: Search paths are scanned recursively, so overlapping paths...
    """
    for path1, path2 in combinations(path_strings, 2):
        if Path(path1).is_relative_to(path2) or Path(path2).is_relative_to(path1):
            print_and_raise(
                "Search paths are scanned recursively, "
                f"so overlapping paths ({path1} and {path2}) are not allowed."
            )


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
