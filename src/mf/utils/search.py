import json
from datetime import datetime

import typer
from rich.panel import Panel
from rich.table import Table

from .console import console, print_and_raise
from .file import FileResult, FileResults, get_search_cache_file
from .playlist import get_last_played_index


def print_search_results(title: str, results: FileResults):
    """Render a table of search results.

    Args:
        title (str): Title displayed above table.
        results (FileResults): Search results.
    """
    max_index_width = len(str(len(results))) if results else 1
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=max_index_width, justify="right")
    table.add_column("File", style="green", overflow="fold")
    table.add_column("Location", style="blue", overflow="fold")

    last_played_index = get_last_played_index()

    for idx, result in enumerate(results):
        is_last_played = idx == last_played_index

        if is_last_played:
            # Highlight last played file in the search results
            table.add_row(
                f"[bright_cyan]{str(idx + 1)}[/bright_cyan]",
                f"[bright_cyan]{result.file.name}[/bright_cyan]",
                str(result.file.parent),
            )
        else:
            table.add_row(str(idx + 1), result.file.name, str(result.file.parent))

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

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)


def load_search_results() -> tuple[str, FileResults, datetime]:
    """Load cached search results.

    Raises:
        typer.Exit: If cache is missing or invalid.

    Returns:
        tuple[str, FileResults, datetime]: Pattern, results, timestamp.
    """
    cache_file = get_search_cache_file()
    try:
        with open(cache_file, encoding="utf-8") as f:
            cache_data = json.load(f)

        pattern = cache_data["pattern"]
        results = FileResults.from_paths(cache_data["results"])
        timestamp = datetime.fromisoformat(cache_data["timestamp"])

        return pattern, results, timestamp
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
    pattern, results, _ = load_search_results()

    try:
        result = results[index - 1]
    except IndexError as e:
        console.print(
            f"Index {index} not found in last search results (pattern: '{pattern}'). "
            f"Valid indices: 1-{len(results)}.",
            style="red",
        )
        raise typer.Exit(1) from e

    if not result.file.exists():
        print_and_raise(f"File no longer exists: {result.file}.")

    return result
