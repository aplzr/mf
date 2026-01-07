"""Last search results management commands.

Provides a Typer sub-application for viewing and managing cached search results
from the most recent query. The last search cache enables quick re-access to
previous results without re-scanning the filesystem.

Command Structure:
    mf last         # Show last search results (default command)
    mf last show    # Show last search results with metadata
    mf last file    # Print search cache file location
    mf last clear   # Delete the search cache

Features:
    - Default command behavior: 'mf last' runs 'mf last show'
    - Displays search pattern and timestamp with results
    - Highlights last played item in results table
    - Path display controlled by 'display_paths' config setting
"""

from __future__ import annotations

import typer

from .utils.config import build_config
from .utils.console import console, print_ok
from .utils.file import get_search_cache_file
from .utils.search import load_search_results, print_search_results

app_last = typer.Typer(
    help=(
        "Show or clear results of the last file search, print search results file "
        "location. If no argument is given, runs the default 'show' command."
    )
)


@app_last.command()
def show():
    """Print last search results."""
    results, pattern, timestamp = load_search_results()
    console.print(f"[yellow]Cache file:[/yellow] {get_search_cache_file()}")
    console.print(f"[yellow]Timestamp:[/yellow] [grey70]{str(timestamp)}[/grey70]")
    console.print("[yellow]Cached results:[/yellow]")

    if "latest additions" not in pattern:
        pattern = f"Search pattern: {pattern}"

    print_search_results(pattern, results, build_config().display_paths)


@app_last.command()
def file():
    """Print the search results file location."""
    print(get_search_cache_file())


@app_last.command()
def clear():
    """Clear last search results."""
    get_search_cache_file().unlink(missing_ok=True)
    print_ok("Cache cleared.")


@app_last.callback(invoke_without_command=True)
def cache_callback(ctx: typer.Context):
    """Runs the default subcommand 'show' when no argument to 'last' is provided."""
    if ctx.invoked_subcommand is None:
        show()
