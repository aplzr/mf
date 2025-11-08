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
    "get_cache_file",
    "save_search_results",
    "load_search_results",
    "print_search_results",
    "get_file_by_index",
]


def get_cache_file() -> Path:
    """Return path to cache file.

    Args:
        None

    Returns:
        Path: Location of the JSON cache file (platform aware; falls back to
        ~/.cache/mf on POSIX).
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
    return cache_dir / "last_search.json"


def save_search_results(pattern: str, results: list[tuple[int, Path]]) -> None:
    """Persist search results to cache.

    Args:
        pattern (str): Search pattern used.
        results (list[tuple[int, Path]]): Indexed file path results.

    Returns:
        None
    """
    cache_data = {
        "pattern": pattern,
        "timestamp": datetime.now().isoformat(),
        "results": [
            {"index": idx, "path": file_path.as_posix()} for idx, file_path in results
        ],
    }

    cache_file = get_cache_file()

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)


def load_search_results() -> tuple[str, list[tuple[int, Path]], datetime]:
    """Load cached search results.

    Raises:
        typer.Exit: If cache is missing or invalid.

    Returns:
        tuple[str, list[tuple[int, Path]], datetime]: Pattern, results, timestamp.
    """
    cache_file = get_cache_file()
    try:
        with open(cache_file, encoding="utf-8") as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = [
            (item["index"], Path(item["path"])) for item in cache_data["results"]
        ]
        timestamp = datetime.fromisoformat(cache_data["timestamp"])

        return pattern, results, timestamp
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print_error(
            "Cache is empty or doesn't exist. "
            "Please run 'mf find <pattern>' or 'mf new' first."
        )
        raise typer.Exit(1) from e


def print_search_results(title: str, results: list[tuple[int, Path]]):
    """Render a table of search results.

    Args:
        title (str): Title displayed above table.
        results (list[tuple[int, Path]]): Indexed search results.
    """
    max_index_width = len(str(len(results))) if results else 1
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green", overflow="fold")
    table.add_column("Location", style="blue", overflow="fold")

    for idx, path in results:
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
    file = None

    for idx, path in results:
        if idx == index:
            file = path
            break

    if file is None:
        console.print(
            f"Index {index} not found in last search results (pattern: '{pattern}').",
            style="red",
        )
        console.print(f"Valid indices: 1-{len(results)}.", style="yellow")
        raise typer.Exit(1)

    if not file.exists():
        console.print(f"[red]File no longer exists:[/red] {file}.")
        raise typer.Exit(1)

    return file
