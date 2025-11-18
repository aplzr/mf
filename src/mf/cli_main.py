import os
import subprocess
from pathlib import Path
from random import randrange

import typer
from guessit import guessit
from imdbinfo import search_title

from .cli_cache import app_cache
from .cli_config import app_config
from .cli_last import app_last
from .utils.config import read_config
from .utils.console import console, print_error, print_warn
from .utils.file import (
    FindQuery,
    NewQuery,
    get_result_by_index,
    print_search_results,
    save_search_results,
)
from .version import __version__

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
    results = FindQuery(pattern).execute()

    if not results:
        console.print(f"No media files found matching '{pattern}'", style="yellow")
        raise typer.Exit()

    save_search_results(pattern, results)
    print_search_results(f"Search pattern: {pattern}", results)


@app_mf.command()
def new(
    n: int = typer.Argument(20, help="Number of latest additions to show"),
):
    """Find the latest additions to the media database."""
    newest_files = NewQuery(n).execute()
    pattern = f"{n} latest additions"

    if not newest_files:
        console.print("No media files found (empty collection).", style="yellow")
        raise typer.Exit()

    save_search_results(pattern, newest_files)
    print_search_results(pattern, newest_files)


@app_mf.command()
def play(
    index: int = typer.Argument(
        None, help="Index of the file to play. If None, plays a random file."
    ),
):
    """Play a media file by its index."""
    if index:
        # Play requested file
        file_to_play = get_result_by_index(index)

    else:
        # Play random file
        all_files = FindQuery("*").execute()
        file_to_play = all_files[randrange(len(all_files))]

    console.print(f"[green]Playing:[/green] {file_to_play.file.name}")
    console.print(f"[blue]Location:[/blue] [white]{file_to_play.file.parent}[/white]")

    # Launch VLC with the file
    try:
        if os.name == "nt":  # Windows
            # Try common VLC installation paths
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ]
            vlc_cmd = None
            for path in vlc_paths:
                if Path(path).exists():
                    vlc_cmd = path
                    break

            if vlc_cmd is None:
                # Try to find in PATH
                vlc_cmd = "vlc"
        else:  # Unix-like (Linux, macOS)
            vlc_cmd = "vlc"

        fullscreen_playback = read_config().get("fullscreen_playback", True)
        vlc_args = [vlc_cmd, str(file_to_play.file)]

        if fullscreen_playback:
            vlc_args.extend(["--fullscreen", "--no-video-title-show"])

        # Launch VLC in background
        subprocess.Popen(
            vlc_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        console.print("[green]✓[/green] VLC launched successfully")

    except FileNotFoundError as e:
        console.print(
            "Error: VLC not found. Please install VLC media player.", style="red"
        )
        raise typer.Exit(1) from e

    except Exception as e:
        console.print(f"Error launching VLC: {e}", style="red")
        raise typer.Exit(1) from e


@app_mf.command()
def imdb(
    index: int = typer.Argument(
        ..., help="Index of the file for which to retrieve the IMDB URL"
    ),
):
    """Open IMDB entry of a search result."""
    filestem = get_result_by_index(index).file.stem
    parsed = guessit(filestem)

    if "title" not in parsed:
        print_warn(f"Could not parse a title from filename '{filestem}'.")
        raise typer.Exit(1)

    title = parsed["title"]
    results = search_title(title)

    if results.titles:
        imdb_url = results.titles[0].url
        console.print(f"IMDB entry for [green]{title}[/green]: {imdb_url}")
        typer.launch(imdb_url)
    else:
        print_error("No IMDB results found for parsed title {title}.")


@app_mf.command()
def filepath(
    index: int = typer.Argument(
        ..., help="Index of the file for which to print the filepath."
    ),
):
    """Print filepath of a search result."""
    print(get_result_by_index(index).file)


@app_mf.command()
def version():
    "Print version."
    console.print(__version__)


@app_mf.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Show help when no command is provided."""
    if ctx.invoked_subcommand is None:
        console.print("")
        console.print(f" Version: {__version__}", style="bright_yellow")
        console.print(ctx.get_help())
        raise typer.Exit()
