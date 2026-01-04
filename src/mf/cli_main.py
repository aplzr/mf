"""Top-level command-line interface.

Main CLI entry point that defines all top-level commands and command groups. Uses Typer
for argument parsing and command routing. All business logic is delegated to utility
modules - this file only handles CLI concerns.

Command Structure:
    mf                    # Show help and version
    mf find <pattern>     # Search for files
    mf new [n]            # Show newest files
    mf play [target]      # Play a file
    mf imdb <index>       # Open IMDB page
    mf filepath <index>   # Print file path
    mf version [check]    # Version info/check
    mf cleanup            # Delete config and cache
    mf stats              # Show library statistics

    mf last ...           # Last played commands (sub-app)
    mf config ...         # Configuration commands (sub-app)
    mf cache ...          # Cache commands (sub-app)

Design Philosophy:
    Commands are thin wrappers around utility functions. This keeps the CLI
    layer focused on user interaction while keeping business logic testable
    and reusable. Each command typically:
    1. Parses arguments with Typer
    2. Calls utility function(s)
    3. Displays results or exits

Error Handling:
    Most error handling is delegated to utility functions which use
    print_and_raise() for user-friendly error messages. Typer automatically
    converts typer.Exit(1) to proper exit codes.

Examples:
    $ mf find "*.mkv"           # Find MKV files
    $ mf new 10                 # Show 10 newest files
    $ mf play next              # Play next in playlist
    $ mf play 5                 # Play file at index 5
    $ mf config set video_player mpv
    $ mf cache rebuild
"""

from __future__ import annotations

from typing import cast

import typer

from .cli_cache import app_cache
from .cli_config import app_config
from .cli_last import app_last
from .utils.cache import load_library
from .utils.config import get_config
from .utils.console import console, print_and_raise, print_columns, print_warn
from .utils.file import cleanup
from .utils.misc import open_imdb_entry
from .utils.play import launch_video_player, resolve_play_target
from .utils.scan import FindQuery, NewQuery
from .utils.search import get_result_by_index, print_search_results, save_search_results
from .utils.stats import (
    StatsLayout,
    make_extension_histogram,
    make_filesize_histogram,
    make_resolution_histogram,
)
from .version import __version__, check_version

app_mf = typer.Typer(help="Media file finder and player")
app_mf.add_typer(app_last, name="last")
app_mf.add_typer(app_config, name="config")
app_mf.add_typer(app_cache, name="cache")


@app_mf.command()
def find(
    pattern: str = typer.Argument(
        "*",
        help=(
            "Search pattern (glob-based). Use quotes around patterns with wildcards "
            "to prevent shell expansion (e.g., 'mf find \"*.mp4\"'). If no wildcards "
            "are present, the pattern will be wrapped with wildcards automatically."
        ),
    ),
):
    """Find media files matching the search pattern.

    Finds matching files and prints an indexed list.
    """
    # Find, cache, and print media file paths
    query = FindQuery.from_config(pattern)
    results = query.execute()

    if not results:
        print_warn(f"No media files found matching '{query.pattern}'")
        raise typer.Exit(0)

    display_paths = bool(get_config()["display_paths"])
    save_search_results(query.pattern, results)
    print_search_results(f"Search pattern: {query.pattern}", results, display_paths)


@app_mf.command()
def new(
    n: int = typer.Argument(20, help="Number of latest additions to show"),
):
    """Find the latest additions to the media database."""
    newest_files = NewQuery.from_config(n).execute()
    pattern = f"{n} latest additions"
    display_paths = bool(get_config()["display_paths"])

    if not newest_files:
        print_and_raise("No media files found (empty collection).")

    save_search_results(pattern, newest_files)
    print_search_results(pattern, newest_files, display_paths)


@app_mf.command()
def play(
    target: str = typer.Argument(
        None,
        help=(
            "Index of the file to play or 'next' to play the next search result or "
            "'list' to play last search results as a playlist. If None, plays a random "
            "file."
        ),
    ),
):
    """Play a media file by its index."""
    file_to_play = resolve_play_target(target)
    launch_video_player(file_to_play)


@app_mf.command()
def imdb(
    index: int = typer.Argument(
        ..., help="Index of the file for which to retrieve the IMDB URL"
    ),
):
    """Open IMDB entry of a search result."""
    open_imdb_entry(get_result_by_index(index))


@app_mf.command()
def filepath(
    index: int = typer.Argument(
        ..., help="Index of the file for which to print the filepath."
    ),
):
    """Print filepath of a search result."""
    print(get_result_by_index(index).file)


@app_mf.command()
def version(
    target: str = typer.Argument(
        None,
        help="None or 'check'. If None, displays mediafinder's version. "
        "If 'check', checks if a newer version is available.",
    ),
):
    "Print version or perform version check."
    if target and target == "check":
        check_version()
    else:
        console.print(__version__)


@app_mf.command(name="cleanup")
def cleanup_mf():
    """Reset mediafinder by deleting configuration and cache files.

    Lists files and prompts for confirmation before files are deleted. Use for cleanup
    before uninstalling or for a factory reset.
    """
    cleanup()


@app_mf.command()
def stats():
    """Show library statistics.

    Loads library metadata from cache if caching is activated, otherwise performs a
    fresh filesystem scan to compute library statistics.
    """
    cfg = get_config()
    configured_extensions = cast(list[str], cfg["media_extensions"])
    results = load_library()
    layout = StatsLayout.from_terminal()
    panels = []

    if configured_extensions:
        results_filtered = results.copy()
        results_filtered.filter_by_extension(configured_extensions)

    # Create statistics
    panels.append(make_extension_histogram(results, type="all_files", layout=layout))
    panels.append(make_resolution_histogram(results, layout))

    if configured_extensions:
        panels.append(
            make_extension_histogram(
                results_filtered, type="media_files", layout=layout
            )
        )
        panels.append(make_filesize_histogram(results_filtered, layout))

    # Render statistics in a multi-column layout
    print_columns(panels, n_columns=layout.n_columns, padding=layout.padding)


@app_mf.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Show help when no command is provided."""
    if ctx.invoked_subcommand is None:
        console.print("")
        console.print(f" Version: {__version__}", style="bright_yellow")
        console.print(ctx.get_help())
        raise typer.Exit()
