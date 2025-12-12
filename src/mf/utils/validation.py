from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .config import get_config
from .console import print_and_raise, print_warn

if TYPE_CHECKING:
    from .cache import CacheData


def validate_search_paths() -> list[Path]:
    """Return existing configured search paths.

    Raises:
        typer.Exit: If no valid search paths are configured.

    Returns:
        list[Path]: List of validated existing search paths.
    """
    search_paths = get_config()["search_paths"]
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


def validate_cache_structure(data: dict) -> CacheData:
    """Validate that cache has the required structure."""
    if not isinstance(data, dict):
        raise ValueError("Cache must be a dictionary.")

    if "timestamp" not in data or "files" not in data:
        raise ValueError("Cache missing required keys.")

    if not isinstance(data["files"], list):
        raise ValueError("Cache 'files' must be a list.")

    return data
