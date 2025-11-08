from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from .console import console, print_error

__all__ = [
    "get_file_by_index",
    "get_library_cache_file",
    "get_search_cache_file",
    "load_search_results",
    "print_search_results",
    "save_search_results",
]


def get_cache_dir() -> Path:
    """Return path to the cache directory.

    Platform aware with fallback to ~/.cache.

    Returns:
        Path: Cache directory.
    """
    cache_dir = (
        Path(
            os.environ.get(
                "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME",
                Path.home() / ".cache",
            ),
        )
        / "mf"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    return cache_dir


def get_search_cache_file() -> Path:
    """Return path to the search cache file.

    Returns:
        Path: Location of the JSON search cache file.
    """
    return get_cache_dir() / "last_search.json"


def get_library_cache_file() -> Path:
    """Return path to the library cache file.

    Returns:
        Path: Location of the JSON library cache file.
    """
    return get_cache_dir() / "library.json"


def save_search_results(pattern: str, results: list[Path]) -> None:
    """Persist search results to cache.

    Args:
        pattern (str): Search pattern used.
        results (list[Path]): Search results.
    """
    cache_data = {
        "pattern": pattern,
        "timestamp": datetime.now().isoformat(),
        "results": [file_path.as_posix() for file_path in results],
    }

    cache_file = get_search_cache_file()

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)


def load_search_results() -> tuple[str, list[Path], datetime]:
    """Load cached search results.

    Raises:
        typer.Exit: If cache is missing or invalid.

    Returns:
        tuple[str, list[Path], datetime]: Pattern, results, timestamp.
    """
    cache_file = get_search_cache_file()
    try:
        with open(cache_file, encoding="utf-8") as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = [Path(path_str) for path_str in cache_data["results"]]
        timestamp = datetime.fromisoformat(cache_data["timestamp"])

        return pattern, results, timestamp
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print_error(
            "Cache is empty or doesn't exist. "
            "Please run 'mf find <pattern>' or 'mf new' first."
        )
        raise typer.Exit(1) from e


def print_search_results(title: str, results: list[Path]):
    """Render a table of search results.

    Args:
        title (str): Title displayed above table.
        results (list[Path]): Search results.
    """
    max_index_width = len(str(len(results))) if results else 1
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green", overflow="fold")
    table.add_column("Location", style="blue", overflow="fold")

    for idx, path in enumerate(results, start=1):
        table.add_row(str(idx), path.name, str(path.parent))

    panel = Panel(
        table, title=f"[bold]{title}[/bold]", title_align="left", padding=(1, 1)
    )
    console.print()
    console.print(panel)


def get_file_by_index(index: int) -> Path:
    """Retrieve file path by index.

    Args:
        index (int): Index of desired file.

    Raises:
        typer.Exit: If index not found or file no longer exists.

    Returns:
        Path: File path for the given index.
    """
    pattern, results, _ = load_search_results()

    try:
        file = results[index - 1]
    except IndexError as e:
        console.print(
            f"Index {index} not found in last search results (pattern: '{pattern}'). "
            f"Valid indices: 1-{len(results)}.",
            style="red",
        )
        raise typer.Exit(1) from e

    if not file.exists():
        print_error(f"File no longer exists: {file}.")

    return file
