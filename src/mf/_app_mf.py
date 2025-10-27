import os
import subprocess
from pathlib import Path
from random import randrange

import typer
from guessit import guessit
from imdb import IMDb

from ._app_cache import app_cache
from ._app_config import app_config
from ._version import __version__
from .utils import (
    console,
    find_media_files,
    get_file_by_index,
    normalize_pattern,
    print_search_results,
    save_search_results,
)

app_mf = typer.Typer(help="Media file finder and player")
app_mf.add_typer(app_cache, name="cache")
app_mf.add_typer(app_config, name="config")


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
    pattern = normalize_pattern(pattern)
    results = find_media_files(pattern)

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
    newest_files = find_media_files("*", sort_by_mtime=True)[:n]
    pattern = f"{n} latest additions"
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
        file_to_play = get_file_by_index(index)

    else:
        # Play random file
        all_files = find_media_files("*")
        _, file_to_play = all_files[randrange(len(all_files))]

    console.print(f"[green]Playing:[/green] {file_to_play.name}")
    console.print(f"[blue]Location:[/blue] {file_to_play.parent}")

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

        # Launch VLC in background
        subprocess.Popen(
            [vlc_cmd, str(file_to_play)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        console.print("[green]✓[/green] VLC launched successfully")

    except FileNotFoundError:
        console.print(
            "Error: VLC not found. Please install VLC media player.", style="red"
        )
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"Error launching VLC: {e}", style="red")
        raise typer.Exit(1)


@app_mf.command()
def imdb(
    index: int = typer.Argument(
        ..., help="Index of the file for which to retrieve the IMDB URL"
    ),
):
    """Open IMDB entry of a search result."""
    filestem = get_file_by_index(index).stem
    title = guessit(filestem)["title"]
    imdb_entry = IMDb().search_movie(title)[0]
    imdb_url = f"https://www.imdb.com/title/tt{imdb_entry.movieID}/"
    console.print(f"IMDB entry for [green]{imdb_entry['title']}[/green]: {imdb_url}")
    typer.launch(imdb_url)


@app_mf.command()
def filepath(
    index: int = typer.Argument(
        ..., help="Index of the file for which to print the filepath."
    ),
):
    """Print filepath of a search result."""
    print(get_file_by_index(index))


@app_mf.command()
def version():
    "Print version."
    console.print(__version__)


# TODOs
# - [ ] Add "trailer" command
# - [ ] Add -r option for additional ratings
