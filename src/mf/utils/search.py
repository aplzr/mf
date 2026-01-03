"""Search result management and display.

Handles presentation and persistence of search results. Provides table-based display
with Rich formatting and JSON-based caching for quick access to the last search.

Features:
    - Rich table display with optional path column
    - Last played item highlighting
    - JSON cache for persisting search results
    - 1-based indexing for user-friendly access

Cache Format:
    JSON file stored in XDG_CACHE_HOME/mf/last_search.json containing:
    {
        "pattern": "search pattern used",
        "timestamp": "2024-01-01T12:00:00.123456",
        "results": ["/path/to/file1.mkv", "/path/to/file2.mp4", ...]
    }

Display Format:
    Results are shown in a Rich table with:
    - 1-based index numbers (cyan)
    - File names (green)
    - Optional parent paths (blue)
    - Last played item highlighted in bright cyan

Index Convention:
    All functions use 1-based indexing to match the display. Internally
    converted to 0-based for list access.

Examples:
    >>> # Display results
    >>> results, pattern, _ = load_search_results()
    >>> print_search_results(pattern, results, display_paths=True)

    >>> # Save and load results
    >>> save_search_results("*.mkv", results)
    >>> loaded_results, pattern, timestamp = load_search_results()

    >>> # Get specific result by index
    >>> file = get_result_by_index(1)  # First result
"""

from __future__ import annotations

import json
from datetime import datetime

from rich.panel import Panel
from rich.table import Table

from .console import console, print_and_raise
from .file import FileResult, FileResults, get_search_cache_file, open_utf8
from .playlist import get_last_played_index


def print_search_results(title: str, results: FileResults, display_paths: bool):
    """Render a table of search results.

    Args:
        title (str): Title displayed above table.
        results (FileResults): Search results.
        display_paths (bool): Whether to display file paths.
    """
    # TODO: Change signature to
    # print_search_results(results: FileResults, title: str, display_paths: bool)
    max_index_width = len(str(len(results))) if results else 1

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green", overflow="fold")

    if display_paths:
        table.add_column("Location", style="blue", overflow="fold")

    last_played_index = get_last_played_index()

    for idx, result in enumerate(results):
        is_last_played = idx == last_played_index

        idx_str = (
            f"[bright_cyan]{str(idx + 1)}[/bright_cyan]"
            if is_last_played
            else str(idx + 1)
        )
        name_str = (
            f"[bright_cyan]{result.file.name}[/bright_cyan]"
            if is_last_played
            else result.file.name
        )
        path_str = str(result.file.parent)

        row_elements = (
            [idx_str, name_str, path_str] if display_paths else [idx_str, name_str]
        )
        table.add_row(*row_elements)

    panel = Panel(
        table, title=f"[bold]{title}[/bold]", title_align="left", padding=(1, 1)
    )
    console.print()
    console.print(panel)


def save_search_results(pattern: str, results: FileResults) -> None:
    """Persist search results to cache.

    Args:
        pattern (str): Search pattern used.
        results (FileResults): Search results.
    """
    cache_data = {
        "pattern": pattern,
        "timestamp": datetime.now().isoformat(),
        "results": [str(result) for result in results],
    }

    cache_file = get_search_cache_file()

    with open_utf8(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)


def load_search_results() -> tuple[FileResults, str, datetime]:
    """Load cached search results.

    Raises:
        typer.Exit: If cache is missing or invalid.

    Returns:
        tuple[FileResults, str, datetime]: Results, pattern, timestamp.
    """
    cache_file = get_search_cache_file()
    try:
        with open_utf8(cache_file) as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = FileResults.from_paths(cache_data["results"])
        timestamp = datetime.fromisoformat(cache_data["timestamp"])

        return results, pattern, timestamp
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print_and_raise(
            "Cache is empty or doesn't exist. "
            "Please run 'mf find <pattern>' or 'mf new' first.",
            raise_from=e,
        )


def get_result_by_index(index: int) -> FileResult:
    """Retrieve result by index.

    Args:
        index (int): Index of desired file.

    Raises:
        typer.Exit: If index not found or file no longer exists.

    Returns:
        FileResult: File for the given index.
    """
    results, pattern, _ = load_search_results()

    try:
        result = results[index - 1]
    except IndexError as e:
        print_and_raise(
            f"Index {index} not found in last search results (pattern: '{pattern}'). "
            f"Valid indices: 1-{len(results)}.",
            raise_from=e,
        )

    return result
